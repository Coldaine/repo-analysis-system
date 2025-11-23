# Using ToolNode for Structured Tool Calls

LangGraph provides a powerful `ToolNode` that simplifies the process of calling tools (functions) from within your graph. It acts as a robust, managed dispatcher that executes tool calls requested by an LLM, handles their outputs, and seamlessly integrates the results back into the graph's state.

This guide covers the essential patterns for using `ToolNode`, including parallel execution, error handling, and routing.

## What is `ToolNode`?

`ToolNode` is a pre-built graph node that:
1.  **Inspects the last message** in the state for tool call requests.
2.  **Executes the requested tool calls**, either sequentially or in parallel.
3.  **Catches and reports errors** from tool executions.
4.  **Returns the results** as `ToolMessage` objects, which are automatically added to the `messages` list in the state.

Using `ToolNode` is highly recommended over calling tools manually within a regular node because it provides a standardized, battle-tested mechanism for tool invocation and error handling.

## Core Pattern: Scatter-Gather with `ToolNode`

The most common pattern for using `ToolNode` is the "scatter-gather" workflow:
1.  **LLM Node (`scatter`)**: An LLM node receives the current state (including conversation history) and decides to call one or more tools to gather information. It returns a message containing `tool_calls`.
2.  **`ToolNode` (`gather`)**: The `ToolNode` receives the LLM's message, executes all requested tool calls in parallel, and appends the results to the `messages` list.
3.  **Loop**: The graph then typically loops back to the LLM node, which now has the tool results available in its context to formulate a final answer.

### Example: A Simple Research Agent

Here is a complete example demonstrating how to define tools, create a `ToolNode`, and wire it into a graph.

```python
from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

# 1. Define Tools

@tool
def search_google(query: str):
    """Searches Google for the given query and returns results."""
    # In a real implementation, this would call the Google Search API.
    print(f"Searching Google for: {query}")
    return f"Results for '{query}': LangGraph is a library for building stateful, multi-actor applications with LLMs."

@tool
def search_wikipedia(query: str):
    """Searches Wikipedia for the given query."""
    print(f"Searching Wikipedia for: {query}")
    return f"Wikipedia entry for '{query}': LangGraph is built on top of LangChain."

# A list of all tools available to the agent
tools = [search_google, search_wikipedia]

# 2. Define State
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# 3. Create the Graph and ToolNode
graph_builder = StateGraph(State)

# LLM Node
llm = ChatOpenAI(model="gpt-4o")
model_with_tools = llm.bind_tools(tools)

def llm_node(state: State):
    return {"messages": [model_with_tools.invoke(state["messages"])]}

graph_builder.add_node("llm", llm_node)

# ToolNode
# This special node executes the tools called by the LLM.
from langgraph.prebuilt import ToolNode

tool_node = ToolNode(tools)
graph_builder.add_node("tools", tool_node)

# 4. Define Edges and Conditional Routing

def should_continue(state: State) -> str:
    """
    A conditional edge that determines the next step.
    If the LLM made tool calls, route to the ToolNode. Otherwise, end.
    """
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"  # Route to the ToolNode
    return END  # End the graph

graph_builder.add_conditional_edges(
    "llm",
    should_continue,
    {
        "tools": "tools",
        "END": END,
    },
)

# The ToolNode always routes back to the LLM node to process the tool results.
graph_builder.add_edge("tools", "llm")
graph_builder.set_entry_point("llm")

graph = graph_builder.compile()

# Run the graph
initial_state = {"messages": [HumanMessage(content="What is LangGraph?")]}
final_state = graph.invoke(initial_state)

print(final_state["messages"][-1].content)
```

### How It Works:
1.  The `llm_node` invokes the model, which returns an `AIMessage` containing requests to call `search_google` and `search_wikipedia`.
2.  The `should_continue` edge inspects this message. Since `tool_calls` is present, it routes the graph to the `tools` node.
3.  The `ToolNode` executes both `search_google` and `search_wikipedia` in parallel.
4.  It appends the results to the state as two `ToolMessage` objects.
5.  The graph follows the edge from `tools` back to `llm`.
6.  The `llm_node` is invoked again, but this time the `messages` list includes the `ToolMessage` results. The LLM uses this new information to synthesize a final answer.
7.  The LLM's new response has no `tool_calls`, so `should_continue` routes to `END`.

## Handling Tool Errors

If a tool execution fails, `ToolNode` automatically catches the exception and appends a `ToolMessage` with the error details. This allows the LLM to see the error and potentially try again or report the failure.

```python
@tool
def faulty_tool(query: str):
    """This tool always fails."""
    raise ValueError("This tool is broken!")

# If the LLM calls faulty_tool, the ToolNode will append a ToolMessage like this:
# ToolMessage(
#     content='ValueError("This tool is broken!")',
#     tool_call_id="..."
# )
```

## `return_direct` and Ending Execution

Sometimes, you want a tool to be the final step in a graph. For example, a tool that sends an email or saves a file doesn't need to return any information to the LLM.

You can signal this by having the LLM invoke a tool and setting `return_direct=True` in the graph.

To handle this, you can add a check in your conditional routing function.

```python
def should_continue_with_return_direct(state: State) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        # A real agent would have logic to determine if the tool call
        # is one that should end the graph.
        if any(call.get("name") == "send_email" for call in last_message.tool_calls):
            return "END" # Or route to a specific 'send_email' node
        return "tools"
    return END
```
When a tool is marked as `return_direct`, it's a signal that the graph should terminate after the tool call. Your routing logic should ensure that the graph proceeds to `END` after executing such a tool.
