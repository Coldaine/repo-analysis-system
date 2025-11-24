# Implementation Plan: Blueprint Alignment (LangGraph v1.0 Standard)

**Target Version:** LangGraph v1.0+ (Released Oct 2025)
**Philosophy:** Use standard, pre-built components (`ToolNode`, `bind_tools`) instead of custom loops.

## 1. The "Decisions Agent" as a Sub-Graph
The Forensic Investigator is too complex for a single node. It will be implemented as a **Sub-Graph** (a nested state machine) that can be called by the main graph.

### Sub-Graph Structure
```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

# 1. Define the State
class InvestigatorState(TypedDict):
    conflict_context: str
    hypotheses: List[str]
    evidence: List[str]
    verdict: Optional[str]
    messages: Annotated[List[BaseMessage], add_messages]

# 2. Define the Tools
tools = [git_log, git_blame, git_diff, read_file]
tool_node = ToolNode(tools)

# 3. Define the Agent Node (The Brain)
def investigator_agent(state: InvestigatorState):
    # Bind tools to the model
    model = ModelManager.get_model("claude-3-5-sonnet").bind_tools(tools)
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

## 2. Tooling Implementation (The "Toolbox")
We will use `langchain_core.tools` decorators to create safe, typed tools.

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

## 3. Integration into Main Graph
The main `RepositoryAnalysisGraph` will treat the `investigator_graph` as just another node.

```python
# src/orchestration/graph.py

def call_investigator(state: GraphState):
    # Transform main state to sub-graph state
    input_state = {
        "conflict_context": state.conflicts,
        "messages": [HumanMessage(content="Investigate this conflict...")]
    }
    
    # Invoke the sub-graph
    result = investigator_graph.invoke(input_state)
    
    # Transform result back to main state
    return {"blueprint_verdict": result["verdict"]}

# Add to main graph
workflow.add_node("decisions_agent", call_investigator)
```

## 4. Why This is Better (v1.0 Benefits)
1.  **`tools_condition`**: We don't write `if "tool_calls" in msg:` logic anymore. LangGraph handles the routing.
2.  **`ToolNode`**: We don't write the loop to execute tools. LangGraph executes them and appends `ToolMessage` outputs automatically.
3.  **Checkpointing**: Because it's a graph, we can save the state *during* the investigation. If the agent gets stuck, we can resume from the middle.
