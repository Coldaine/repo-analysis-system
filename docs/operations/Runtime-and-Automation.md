# Runtime and Automation

**Status**: Canonical
**Last Updated**: November 23, 2025

## ⚙️ Execution Modes

The system supports multiple execution modes via the `scripts/run_graph.py` entry point.
# Runtime and Automation

**Status**: Canonical  
**Last Updated**: November 23, 2025

This document is the operational runbook for executing LangGraph analyses across the portfolio. It focuses on how work is triggered, routed, and guarded. All persistence specifics live in [Checkpointer and Persistence](./Checkpointer-and-Persistence.md).

## ⚙️ Execution Modes

All modes share the same entry point: `scripts/run_graph.py` (always wrapped with `bws run --`).

1. **CLI (Manual)** – Used for ad-hoc debugging and health checks. Supports repo targeting via `--repos`, health probes, and dry runs. Example: `bws run -- python scripts/run_graph.py analyze --repos owner/repo1`.
2. **Webhook (Event-Driven)** – GitHub App/Action validates incoming push/PR/issue events and forwards the payload to the persistent runner’s queue. LangGraph never executes inside GitHub Actions; the action is a stateless forwarder.
3. **Dormant Audit (Cron)** – A 30-minute systemd/cron timer calls into the runner to enqueue repositories whose Repository Charter snapshot is stale or that may have missed events.

Execution mode determines _how_ work is enqueued, not how the graph runs—the runner normalizes every job into the same workflow.

## 🖥️ Infrastructure Topology

The production deployment runs on `zo.computer` as a long-lived service:

- **Runner Service** – Python orchestrator that pulls jobs from the queue, injects Bitwarden secrets, and executes LangGraph workloads.
- **Node.js Pre-Processor** – Deterministic git/GitHub/CI collector invoked before the graph to build the RepoContext JSON contract.
- **Redis (Queue)** – Applies dedupe + backpressure, collapsing bursts of identical repo/branch events.
- **PostgreSQL** – Stores Repository Charters/intent records, metrics, and LangGraph checkpoints.
- **Repo Cache** – Persistent working tree for all tracked repositories, synchronized by the GitHub Sync Service (clone, fetch, prune loops).

## 🔐 Secrets Injection Snapshot

Secrets are injected at runtime with `bws run` (Bitwarden Secrets Manager). No `.env` files are committed or loaded.

- Required secrets: `GITHUB_TOKEN`, `GITHUB_OWNER`, `GLM_API_KEY`, `MINIMAX_API_KEY`, `POSTGRES_CONNECTION_STRING` (plus optional search keys).
- Local, cron, and CI flows all wrap their invocation with `bws run -- ...` or `bitwarden/sm-action@v1`.
- Configuration details, onboarding steps, and troubleshooting live in [Config and Secrets](./Config-and-Secrets.md).

## 🔄 Automation Workflow

1. **Event Ingest** – Webhook payloads and dormant-audit ticks hit the runner’s `/enqueue` endpoint. Metadata (delivery ID, repo, branch, reason) is persisted before queueing.
2. **Queue Processing** – Redis deduplicates bursts and enforces `max_concurrent_runs`. Jobs leaving the queue are wrapped in a `bws run -- python scripts/run_graph.py --event <payload>` shell.
3. **Deterministic Pre-Processing** – The Node.js layer syncs the repo cache, fetches PR/issue/CI deltas, computes file diffs, and emits a structured RepoContext JSON.
4. **LangGraph Orchestration** – The Python graph ingests RepoContext, initializes state, fans out to agents (Archivist, Architect, Complexity, Security, Forensics), and aggregates results.
5. **Reporting + Publication** – Results are written to PostgreSQL; optional GitHub comments/status checks are emitted with the service `GITHUB_TOKEN`.

## 💾 Checkpointing (Pointer)

Persistent checkpointing is mandatory for resumability and time-travel. Configure `orchestration.langgraph.checkpointer` with Postgres details, monitor thread IDs, and use `graph.invoke(None, config=...)` to resume interrupted runs. Detailed procedures, schema, and troubleshooting were consolidated into [Checkpointer and Persistence](./Checkpointer-and-Persistence.md) to avoid duplication.

## 🧱 Operational Guardrails

- **Concurrency** – Tune `orchestration.langgraph.max_concurrent_runs` alongside Redis queue depth to prevent over-scheduling; prefer shedding load at enqueue time instead of letting LangGraph thrash.
- **Recursion Limit** – Default `recursion_limit` is 25. Hitting it raises `GraphRecursionError`; on failure we emit partial artifacts and fall back to manual review.
- **Burst Control** – Duplicate events (same repo, branch, SHA) within a short TTL are collapsed. Dormant audit jobs include a `reason` tag so operators can distinguish missed-webhook replays from real code changes.

## Related Documents

- [Config and Secrets](./Config-and-Secrets.md) – Detailed Bitwarden setup, configuration schema, and required secret inventory.
- [Checkpointer and Persistence](./Checkpointer-and-Persistence.md) – Deep dive on PostgresSaver, schema, resume/fork flows, and inspection commands.
- [Observability and Reporting](./Observability-and-Reporting.md) – Logging, metrics, tracing, and reporting layers once runs complete.
-   `GLM_API_KEY`: For GLM models.
