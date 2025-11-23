# Implementation Guide (Aligned)

This guide distills the useful implementation patterns from the prior plans while aligning with the locked architecture (`docs/UNIFIED-DECISIONS.md`) and the current goals (`docs/vision-v2-parallel-agents/Implementation-Anchor-Goals.md`).

## Stack Alignment
- Orchestration: Python + LangGraph (primary).
- Pre-processing: Node.js deterministic scripts (git/GitHub/baseline/CI/diff).
- Storage: PostgreSQL for baselines/state/metrics; repo cache on disk.
- Secrets: Bitwarden runtime injection (`bws run`, `bitwarden/sm-action@v1`).
- Scheduling: Webhook-first (push/PR/issue/CI) with 30-minute dormant audit cron.
- Outputs: Progressive disclosure (levels 1–4) with Markdown + visuals.

## LangGraph v1.0 Patterns

### Subgraph Isolation (Decisions/Forensics Agent)
Use a nested graph with a functional wrapper to keep parent state clean and encapsulate tool chatter.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

# Child (investigator) state
class InvestigatorState(TypedDict):
    conflict_context: str
    involved_files: List[str]
    messages: Annotated[List[BaseMessage], add_messages]

# Tools
tools = [git_log, git_blame, git_diff, read_file]
tool_node = ToolNode(tools)

def investigator_agent(state: InvestigatorState, runtime: Runtime):
    model_name = runtime.context.get("model_name", "claude-3-5-sonnet")
    model = ModelManager.get_model(model_name).bind_tools(tools)
    return {"messages": [model.invoke(state["messages"])]}

# Child graph
workflow = StateGraph(InvestigatorState)
workflow.add_node("investigator", investigator_agent)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "investigator")
workflow.add_conditional_edges("investigator", tools_condition)
workflow.add_edge("tools", "investigator")
investigator_graph = workflow.compile()

# Wrapper in parent graph
def call_investigator_wrapper(state: ParentState, runtime: Runtime):
    latest_conflict = state["identified_conflicts"][-1]
    child_input = {
        "conflict_context": latest_conflict.description,
        "involved_files": latest_conflict.files,
        "messages": [HumanMessage(content=f"Investigate: {latest_conflict.description}")],
    }
    child_output = investigator_graph.invoke(child_input, config=runtime.config)
    final_message = child_output["messages"][-1]
    return {
        "blueprint_verdict": final_message.content,
        "messages": [AIMessage(content=f"Investigation Complete: {final_message.content}")],
    }
```

### Runtime/Context Guidance
- Prefer passing a `Runtime` object (or a typed context) into nodes instead of global config dicts. Centralize tracing, stores, and run metadata there.
- When keeping `config` for now, add TODOs for runtime adoption and keep node signatures ready for `runtime`.

### Tooling
- Define tools in `src/tools/*` using `langchain_core.tools` decorators.
- Use `ToolNode` + `tools_condition` instead of manual tool-call loops.
- Keep tool outputs small and scoped (avoid dumping large diffs into messages).

## Checkpointing and Stores
- Default to `MemorySaver` for dev; use a durable checkpointer (e.g., Postgres-backed) in production to survive restarts.
- Use `runtime.store` or equivalent for long-lived artifacts (e.g., blueprint/forensics artifacts) rather than bloating graph state.

## Parallelism and Backpressure
- Use LangGraph fan-out and `orchestration.langgraph.max_concurrent_runs` for concurrency.
- Apply backpressure and duplicate-event collapse at the webhook/job ingress before kicking off runs.
- Long-running work should respect the persistent runner + queue model (GitHub Actions/App stays a thin forwarder).

## Pre-Processing (Deterministic First)
- Run the Node.js pre-processing to gather commits/PRs/issues/diffs/CI/baseline deltas before any LLM calls.
- Emit structured JSON as the contract for downstream agents; treat PR-only diff ingestion as insufficient.

## Reporting
- Generate progressive-disclosure outputs (levels 1–4) and post links via the runner (not from transient CI).
- Keep report templates aligned with the anchor goals; avoid ad-hoc formats.

## Secrets and Ops
- Always run with Bitwarden runtime injection; no stored env files.
- Persistent runner hosts Postgres + repo cache; webhook/App only validates and forwards events plus the dormant audit trigger.
