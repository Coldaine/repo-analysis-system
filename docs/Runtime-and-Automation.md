# Runtime and Automation

**Status**: Canonical
**Last Updated**: November 23, 2025

## ⚙️ Execution Modes

The system supports multiple execution modes via the `scripts/run_graph.py` entry point.

### 1. CLI (Manual)
Run analysis manually for debugging or ad-hoc checks.

```bash
# Full analysis of specific repos
bws run -- python scripts/run_graph.py analyze --repos "owner/repo1" "owner/repo2"

# Health check
bws run -- python scripts/run_graph.py health
```

### 2. Webhook (Event-Driven)
Triggered by GitHub events (Push, PR, Issue).
-   **Payload**: JSON payload from GitHub.
-   **Action**: A thin GitHub App/Action validates the signature and forwards the event to the persistent runner's queue.
-   **Note**: LangGraph **never** runs inside the GitHub Action runner. The Action is purely a forwarder.

### 3. Dormant Audit (Cron)
Runs every 30 minutes to check for repositories that haven't been updated recently but might need a "heartbeat" check or have missed webhooks.
-   **Logic**: Scans for repositories whose Repository Charter snapshot is stale (>X hours) or missing.
-   **Action**: Enqueues jobs only for those needing refresh.

---

## 🖥️ Infrastructure (zo.computer)

The system runs on a persistent VM/Container environment (`zo.computer`).

### Component Stack
1.  **Runner Service**: A Python/Node.js service that consumes the job queue.
2.  **PostgreSQL**: Stores state, Repository Charters/intent records, and metrics.
3.  **Redis**: Job queue for incoming webhook events (configurable; must support dedupe/backpressure).
4.  **Repo Cache**: A persistent disk volume where repositories are cloned and kept in sync.

### GitHub Sync Service
A dedicated service keeps the local `Repo Cache` synchronized with GitHub.
-   **Sync**: Clones missing repos, pulls updates for existing ones.
-   **Prune**: Removes repositories deleted from GitHub.
-   **Optimization**: Uses `git fetch` to minimize bandwidth.

---

## 🔐 Secrets Injection (Bitwarden)

We use **Bitwarden Secrets Manager** (`bws`) to inject secrets at runtime. **No secrets are stored in `.env` files.**

### The `bws run` Pattern
All commands are prefixed with `bws run`. This spawns a child process with the secrets injected as environment variables.

```bash
# Example: Running the orchestrator
bws run -- python scripts/run_graph.py start-worker
```

### Required Secrets
-   `GITHUB_TOKEN`: For API access and cloning.
-   `ANTHROPIC_API_KEY`: For Claude models.
-   `GLM_API_KEY`: For GLM models.
-   `POSTGRES_CONNECTION_STRING`: For database access.

---

## 🔄 Automation Workflow

1.  **Event Ingest**:
    -   **Webhook**: GitHub sends payload -> Action forwards to Redis Queue.
    -   **Cron**: Scheduler checks for dormant repos -> Enqueues to Redis Queue.
2.  **Queue Processing**:
    -   **Deduplication**: Collapses burst events (e.g., 5 commits in 1 minute) into a single job per repo/branch.
    -   **Backpressure**: Respects `max_concurrent_runs` to avoid overloading the runner.
3.  **Pre-Processing (Node.js)**:
    -   Pulls the repo to the `Repo Cache`.
    -   Calculates deterministic diffs (files changed, CI status).
    -   Generates the `RepoContext` JSON.
4.  **Orchestration (LangGraph)**:
    -   Initializes the graph state.
    -   Fans out to parallel agents (Archivist, Architect, etc.).
        -   Checkpointer configuration example (memory vs postgres):

```yaml
orchestration:
    langgraph:
        max_concurrent_runs: 5
        timeout_seconds: 3600
        retry_attempts: 3
        recursion_limit: 25
        checkpointer: postgres  # 'memory' for local dev, 'postgres' for production
```

If you use Postgres as your checkpointer, configure the `POSTGRES_CONNECTION_STRING` via `bws` runtime injection or environment. Sample connection string:

```bash
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/repo_analysis
```

### Resume / Time-Travel with PostgresSaver
PostgresSaver stores serialized checkpoints keyed by `thread_id` and step. You can resume or load a specific checkpoint using the runtime store API or command-line:

```bash
# Resume from a checkpoint (pseudo-command)
python scripts/run_graph.py analyze --resume-thread <thread_id> --checkpoint 5
```

Or in Python, using runtime.store (advanced):

```python
cur_state = runtime.store.get(checkpoint_id)
# load and re-invoke:
result = graph.invoke(cur_state)
```

5.  **Reporting**:
    -   Results are stored in PostgreSQL.
    -   (Optional) Comments are posted back to the GitHub PR/Issue.

## 💾 Checkpointing and Persistence

The system uses **PostgreSQL** for persistent checkpointing, allowing long-running workflows to be paused, resumed, and inspected. This is critical for "human-in-the-loop" workflows and recovering from failures.

### Configuration

Configure the checkpointer in your `config.yaml` (or equivalent) to point to your Postgres instance.

```yaml
orchestration:
  langgraph:
    checkpointer:
      type: postgres
      connection_string: "${POSTGRES_CONNECTION_STRING}" # Injected via environment
      # Optional: Connection pool settings
      pool_size: 5
      max_overflow: 10
```

### Resuming an Interrupted Run

To resume a run, you need the `thread_id` of the interrupted workflow. You can find this in the logs or the database.

```python
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
import os

# 1. Initialize the Checkpointer
# Ensure you have the connection string available
pool = ConnectionPool(conninfo=os.environ["POSTGRES_CONNECTION_STRING"])
checkpointer = PostgresSaver(pool)

# 2. Configure the Run
config = {
    "configurable": {
        "thread_id": "unique-thread-id-123",
        # "checkpoint_id": "optional-specific-checkpoint-uuid" 
    }
}

# 3. Resume Execution
# Passing 'None' as input resumes from the last saved state.
# You can also provide new input to 'steer' the execution.
# graph.invoke(None, config=config)
```

### Time Travel (Forking)

You can also "fork" a previous run by specifying a `checkpoint_id` from the past. This allows you to retry a failed step with different inputs or code fixes.

```python
# Fork from a specific checkpoint
config = {
    "configurable": {
        "thread_id": "unique-thread-id-123",
        "checkpoint_id": "0000-0000-0000-0000" # ID of the checkpoint to fork from
    }
}

# Provide new input to diverge from the old path
# graph.invoke({"messages": [HumanMessage(content="Let's try a different approach.")]}, config=config)
```

## 🧱 Guards and Limits
- **recursion_limit**: Prevents unbounded super-steps; configure via `orchestration.langgraph.recursion_limit` and CLI. Handle `GraphRecursionError` by emitting partial outputs/logs and failing gracefully.
- **Concurrency**: Tune `orchestration.langgraph.max_concurrent_runs`; enforce backpressure/dedupe at ingress to protect the runner.
- **Burst Control**: Collapse duplicate events per repo/branch within a short window; apply queue TTLs to avoid stale jobs.

## 📈 Persistence and Checkpoints

LangGraph's checkpointer system is essential for building resilient, long-running workflows. It automatically saves the state of your graph after each step, allowing you to resume interrupted runs without losing progress.

For detailed examples and advanced usage, see [Checkpointer and Persistence](./Checkpointer-and-Persistence.md).

### Checkpointer Configuration (YAML)

We use `PostgresSaver` to persist graph state to our PostgreSQL database. The checkpointer is configured in your `config.yaml` file.

**Example `config.yaml` Snippet:**

```yaml
orchestration:
  langgraph:
    checkpointer:
      type: postgres
      # The connection string is injected at runtime via Bitwarden
      connection_string: "${POSTGRES_CONNECTION_STRING}" 
      # The table name for storing checkpoints
      table_name: "lg_checkpoints"
```

When the graph is compiled, the application reads this configuration and initializes the `PostgresSaver` instance.

### Resuming an Interrupted Run

If a graph execution is interrupted (e.g., due to a machine restart or a transient error), you can resume it from the last known state using the checkpoint ID. The checkpoint ID is typically the `thread_id` associated with the run.

**Example: Resuming a Graph**

```python
import uuid
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

# Assume 'graph' is your compiled StateGraph
# and 'checkpointer' is your configured PostgresSaver instance.

# A unique ID for this specific run
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

# --- Initial Run (gets interrupted) ---
try:
    initial_state = {"messages": ["step 1"]}
    graph.invoke(initial_state, config=config)
    # ... imagine this crashes after a few steps
except Exception as e:
    print(f"Graph interrupted: {e}")

# --- Resuming the Run ---
# To resume, you invoke the graph again with the *same thread_id*.
# LangGraph's checkpointer will automatically load the last saved state
# for that thread_id and continue from where it left off.

print(f"Resuming run for thread_id: {thread_id}")

# Pass an empty input, as the state is loaded from the checkpoint.
# The graph will resume execution at the step after the last successful one.
resumed_state = graph.invoke(None, config=config)

print("Graph resumed and completed successfully.")
print(resumed_state)
```

This pattern is crucial for the reliability of our system, ensuring that webhook-triggered or cron-initiated analyses can survive infrastructure failures and complete successfully.

## ⚠️ Legacy V1 (Cron Analysis)

*Historical Note*: The V1 system ran as a monolithic 6-hour cron job. This has been superseded by the V2 Event-Driven architecture. The legacy design documents have been archived and removed.
