# Checkpointer and Persistence

**Status**: Canonical  
**Last Updated**: November 23, 2025

Persistent checkpoints are how we turn LangGraph from a best-effort workflow into a reliable system. The runtime executes nodes; the checkpointer records their state so we can resume, audit, or fork any run on demand. This document captures the operational details for the Postgres-backed saver used in production.

## 🔍 At a Glance

- **Thread IDs**: Every invocation **must** include a stable `thread_id`. Without it we cannot load or resume state.
- **Storage**: Each completed node produces a serialized checkpoint row in PostgreSQL (`lg_checkpoints`).
- **Resume**: Call `graph.invoke(None, config={"configurable": {"thread_id": ...}})` to pick up from the last successful node.
- **Fork**: Provide both `thread_id` and `checkpoint_id` (or manually load a snapshot) to explore alternate execution paths.
- **CLI Helper**: `python scripts/run_graph.py analyze --resume-thread <thread> [--checkpoint <ordinal>]` wraps the same behavior for operators.

## Why We Invest

1. **Crash Recovery** – Power loss or process restarts no longer trash hours of agent work.
2. **Human-in-the-Loop** – Operators can pause, inspect intermediate state, then resume or fork with new inputs.
3. **Auditability** – Every checkpoint captures the exact state behind a report, satisfying compliance and RCA needs.
4. **Determinism** – Replaying a checkpoint reproduces observed behavior, making concurrency bugs fixable.

See [Runtime and Automation](./Runtime-and-Automation.md) for when checkpoints are written in the broader workflow.

## Configuration Reference

1. **Schema (auto-created)**

```sql
CREATE TABLE IF NOT EXISTS lg_checkpoints (
    thread_id TEXT PRIMARY KEY,
    checkpoint BYTEA,
    parent_ts TEXT
);
```

2. **`config.yaml` snippet**

```yaml
orchestration:
  langgraph:
    max_concurrent_runs: 5
    retry_attempts: 3
    recursion_limit: 25
    checkpointer:
      type: postgres
      connection_string: "${POSTGRES_CONNECTION_STRING}"
      table_name: "lg_checkpoints"
      pool_size: 5
      max_overflow: 10
```

3. **Compile-time wiring**

```python
import os
from langgraph.checkpoint.postgres import PostgresSaver

db_url = os.environ["POSTGRES_CONNECTION_STRING"]
checkpointer = PostgresSaver.from_conn_string(db_url)
graph = builder.compile(checkpointer=checkpointer)
```

## Resume Playbook

1. **Choose a `thread_id`** – Use delivery IDs, queue IDs, or human-readable tokens per run. Persist it in logs.
2. **Initial Invocation** – `graph.invoke(initial_state, config={"configurable": {"thread_id": tid}})`.
3. **Interruption** – If a node raises, LangGraph stops after checkpointing the last successful node.
4. **Resume** – Re-run `graph.invoke(None, config={"configurable": {"thread_id": tid}})` to continue. Passing `None` tells the runtime to load state from storage.

```python
thread_id = "repo__main__2025-11-23T06:00"
config = {"configurable": {"thread_id": thread_id}}

try:
    graph.invoke(initial_state, config=config)
except Exception as exc:
    print(f"Run paused: {exc}")

resumed = graph.invoke(None, config=config)
print(resumed["messages"][-1])
```

*Tip*: Inspect `checkpointer.get(config)` before resuming to verify exactly which node completed last.

## Time-Travel & Forking

1. **List History** – `checkpointer.list(config)` returns the ordered checkpoints for a thread.
2. **Inspect State** – Grab `history[i].channel_values` to see state after step `i`.
3. **Fork** – Launch a new thread from any snapshot:

```python
history = checkpointer.list({"configurable": {"thread_id": original_tid}})
fork_source = history[3]
fork_config = {"configurable": {"thread_id": "forked-" + original_tid}}
graph.invoke(fork_source.channel_values, config=fork_config)
```

Forks maintain immutability—do not delete the source checkpoints even if the fork becomes the blessed path (record the decision in the ADR log instead).

## Troubleshooting & Guardrails

- **Missing `thread_id`** – Results in “no checkpoint” errors. Ensure every CLI/runner path injects one; the Redis queue ID is a safe default.
- **State Bloat** – Keep `State` lean. Move large artifacts to object storage or runtime context so checkpoints stay small.
- **Schema Migrations** – When adding/removing state keys, support both old and new formats until historical checkpoints age out.
- **Database Hygiene** – Monitor table growth and vacuum schedule. Use TTL pruning for obsolete threads to keep the table performant.
- **Security** – `POSTGRES_CONNECTION_STRING` is injected via Bitwarden; never hardcode credentials in config or source.

## Related Reading

- [Runtime and Automation](./Runtime-and-Automation.md) – Event ingest, queueing, and when checkpoints fire.
- [LangGraph State Model Best Practices](../best-practices-reference.md#langgraph-v10-alignment) – Returning deltas keeps checkpoints minimal and merge-safe.
- [Observability and Reporting](./Observability-and-Reporting.md) – How checkpoint metadata surfaces in logs, traces, and dashboards.
