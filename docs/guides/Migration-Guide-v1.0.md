# Migration Guide: v0.x to v1.0

**Status**: Canonical
**Last Updated**: November 23, 2025

This guide outlines the steps to migrate your LangGraph application from the v0.x `AgentExecutor` and Pydantic-based state model to the v1.0 `StateGraph` architecture with `TypedDict` and explicit reducers.

## 📋 Migration Checklist

- [ ] **Replace `AgentExecutor` with `StateGraph`**: Move from the black-box executor to an explicit graph definition.
- [ ] **Convert State to `TypedDict`**: Replace Pydantic `AgentState` models with `TypedDict`.
- [ ] **Add Explicit Reducers**: Annotate list fields (like `messages`) with `Annotated[list, add_messages]`.
- [ ] **Adopt `ToolNode`**: Replace manual tool execution loops with the pre-built `ToolNode`.
- [ ] **Inject Dependencies via `Runtime`**: Move API clients and DB connections out of the state and into a `Runtime` object.

---

## 1. From `AgentExecutor` to `StateGraph`

**v0.x (Legacy)**
In v0.x, you often used `AgentExecutor` or `create_react_agent` which hid the control flow.

```python
# OLD
from langchain.agents import AgentExecutor, create_openai_tools_agent

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
result = agent_executor.invoke({"input": "hi"})
```

**v1.0 (Canonical)**
In v1.0, you define the graph explicitly. This gives you full control over loops, persistence, and branching.

```python
# NEW
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 1. Define Nodes
def agent_node(state):
    # ... call LLM ...
    return {"messages": [response]}

# 2. Build Graph
workflow = StateGraph(State)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app = workflow.compile()
```

## 2. State Definition: Pydantic vs. TypedDict

**v0.x (Legacy)**
State was often a Pydantic model, which encouraged overwriting fields.

```python
# OLD
class AgentState(BaseModel):
    messages: List[BaseMessage]
    # Implicitly overwritten on every update
```

**v1.0 (Canonical)**
Use `TypedDict` with `Annotated` to define *how* updates are merged.

```python
# NEW
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class State(TypedDict):
    # 'add_messages' ensures new messages are appended, not overwritten
    messages: Annotated[list, add_messages]
```

## 3. Dependency Injection: The Runtime Object

**v0.x (Legacy)**
Dependencies were often passed in the state or via global variables.

```python
# OLD
def node(state):
    api_key = state["api_key"] # Leaks secrets into state/checkpoints
    client = Client(api_key)
```

**v1.0 (Canonical)**
Use the `Runtime` object to pass read-only, request-scoped context.

```python
# NEW
from langgraph.runtime import Runtime

def node(state: State, runtime: Runtime[UserContext]):
    client = runtime.context.api_client # Safe, not persisted
```

## 4. Tool Execution

**v0.x (Legacy)**
Tools were executed implicitly by the `AgentExecutor`.

**v1.0 (Canonical)**
Use `ToolNode` for parallel, safe tool execution.

```python
from langgraph.prebuilt import ToolNode

# Create a node that executes tools requested in the last message
tool_node = ToolNode(tools)
workflow.add_node("tools", tool_node)
```

## 5. Handling `GraphRecursionError`

In v1.0, infinite loops are prevented by `recursion_limit`.

```python
from langgraph.errors import GraphRecursionError

try:
    app.invoke(inputs, config={"recursion_limit": 25})
except GraphRecursionError:
    # Handle graceful fallback or error reporting
    print("Workflow exceeded maximum steps.")
```
