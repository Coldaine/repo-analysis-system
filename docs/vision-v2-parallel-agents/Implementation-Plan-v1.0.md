# Implementation Plan: Blueprint Alignment (LangGraph v1.0 Standard)

**Target Version:** LangGraph v1.0+ (Released Oct 2025)
**Philosophy:** Adhere to "The Definitive Technical Review" standards:
1.  **Pattern B (Functional Wrapper)** for Subgraph composition.
2.  **Runtime Object** for configuration and context (replacing `config` dict).
3.  **The Store** for long-term memory (Archivist).
4.  **ToolNode** for parallel execution.

## 1. The "Decisions Agent" as a Sub-Graph
The Forensic Investigator is implemented as a **Sub-Graph** (a nested state machine) encapsulated by a functional wrapper. This ensures state isolation and prevents the parent graph's context from being polluted by the investigator's internal reasoning steps.

### Sub-Graph Structure
```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command, interrupt

# 1. Define the Schemas (State Isolation)
class InvestigatorInput(TypedDict):
    conflict_context: str
    involved_files: List[str]

class InvestigatorOutput(TypedDict):
    verdict: str
    evidence_summary: str

class InvestigatorState(TypedDict):
    # Internal state
    conflict_context: str
    hypotheses: List[str]
    evidence: List[str]
    messages: Annotated[List[BaseMessage], add_messages]

# 2. Define the Tools
tools = [git_log, git_blame, git_diff, read_file]
tool_node = ToolNode(tools)

# 3. Define the Agent Node (The Brain)
# V1.0 Standard: Use Runtime object for config/context
def investigator_agent(state: InvestigatorState, runtime: Runtime):
    # Access config via runtime.context instead of config dict
    model_name = runtime.context.get("model_name", "claude-3-5-sonnet")
    
    # Bind tools to the model
    model = ModelManager.get_model(model_name).bind_tools(tools)
    return {"messages": [model.invoke(state["messages"])]}

# 4. Build the Graph
workflow = StateGraph(InvestigatorState)
workflow.add_node("investigator", investigator_agent)
workflow.add_node("tools", tool_node)

# Standard ReAct Loop
workflow.add_edge(START, "investigator")
workflow.add_conditional_edges("investigator", tools_condition) # Auto-routes to 'tools' or END
workflow.add_edge("tools", "investigator") # Loop back to agent after tool use

investigator_graph = workflow.compile()
```

## 2. Functional Wrapper Encapsulation (The "Isolation" Pattern)
We do NOT add the `investigator_graph` directly to the parent. We use a wrapper node to handle Down-Mapping and Up-Mapping.

```python
# src/orchestration/graph.py

def call_investigator_wrapper(state: ParentState, runtime: Runtime):
    """
    Wrapper node to invoke the investigator subgraph.
    Acts as a firewall between ParentState and InvestigatorState.
    """
    
    # 1. Down-Mapping: Isolate context
    # We extract only what the investigator needs
    latest_conflict = state["identified_conflicts"][-1]
    child_input = {
        "conflict_context": latest_conflict.description,
        "involved_files": latest_conflict.files,
        "messages": [HumanMessage(content=f"Investigate: {latest_conflict.description}")]
    }
    
    # 2. Invocation: Execute the subgraph
    # This is a blocking call from the parent's perspective
    # We pass the runtime config down to the child
    child_output = investigator_graph.invoke(child_input, config=runtime.config)
    
    # 3. Up-Mapping: Bubble up the verdict
    # We extract only the final verdict, ignoring the internal tool calls/messages
    final_message = child_output["messages"][-1]
    
    # Optional: Save to Long-Term Store
    # runtime.store.put(latest_conflict.id, "verdict", final_message.content)
    
    return {
        "blueprint_verdict": final_message.content,
        # Optional: Append a summary message to parent history
        "messages": [AIMessage(content=f"Investigation Complete: {final_message.content}")]
    }

# Add to main graph
workflow.add_node("decisions_agent", call_investigator_wrapper)

## 5. Runtime & State Shape Guidance (v1.0 Alignment)
The current codebase uses a configuration dict (`config`) and class-level dependency injection in many places. LangGraph v1.0 recommends adopting the `Runtime` object pattern for two reasons:

- `Runtime` centralizes typed context, stores, tracing metadata, and other utilities and is passed explicitly to nodes.
- It enables better IDE/static-analysis support and cleaner testing/mocking for node functions.

Recommended migration path:
1. Start by creating a light-weight `Context` TypedDict or dataclass with the keys you need (user_id, thread_id, etc.).
2. Optionally import `Runtime` from `langgraph.runtime` and wire it in your invocation code; it can be created per run and passed to nodes as context.
3. Update node signatures to accept an optional `runtime` parameter and prefer `runtime.context` over `config` lookups.

Example:
```python
from dataclasses import dataclass
from langgraph.runtime import Runtime

@dataclass
class UserContext:
    user_id: int
    thread_id: str

initial_runtime = Runtime(context=UserContext(user_id=42, thread_id='abc'))
result = graph.invoke(state, config={'recursion_limit': 25}, runtime=initial_runtime)
```

If the repo prefers to keep `config` for now, document the plan and add TODO markers where a Runtime conversion should happen.
```

## 3. Tooling Implementation (The "Toolbox")
We will use `langchain_core.tools` decorators to create safe, typed tools. We will also implement **Dynamic Interrupts** for sensitive operations if needed (though read-only git ops are generally safe).

### `src/tools/git_tools.py`
```python
from langchain_core.tools import tool
import subprocess

@tool
def git_log(file_path: str, limit: int = 5) -> str:
    """
    Get the commit history for a specific file.
    Useful for determining when a file was last modified and by whom.
    """
    # Implementation using subprocess.run(["git", "log", ...])
    ...

@tool
def git_diff(commit_a: str, commit_b: str) -> str:
    """
    Get the diff between two commits to understand what changed.
    Useful for analyzing 'Pivot Commits'.
    """
    ...
```

## 4. Why This is Better (v1.0 Benefits)
1.  **State Isolation**: The parent graph doesn't get cluttered with 50+ messages of "git log", "git blame", etc. Only the final verdict bubbles up.
2.  **`tools_condition`**: We don't write `if "tool_calls" in msg:` logic anymore. LangGraph handles the routing.
3.  **`ToolNode`**: We don't write the loop to execute tools. LangGraph executes them and appends `ToolMessage` outputs automatically.
4.  **Checkpointing**: Because it's a graph, we can save the state *during* the investigation. If the agent gets stuck, we can resume from the middle.

## 5. Future: The Archivist & The Store
For the Archivist agent, we will leverage `runtime.store` to persist the "Blueprint" (Architectural Pillars) across sessions, rather than just passing it in the graph state. This allows the Blueprint to evolve and be referenced by other threads.

**Persistence Guidance**: For local development, `MemorySaver` is a fine default. For production deployments, prefer a durable checkpointer like `PostgresSaver` (or other database-backed saver) so that graph state survives restarts, and long-running threads can be resumed across service restarts. Align your `orchestration.langgraph.checkpointer` configuration to `postgres` in production.
