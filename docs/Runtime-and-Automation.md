# Runtime and Automation

**Status**: Canonical
**Last Updated**: November 23, 2025

## ⚙️ Execution Modes

The system supports multiple execution modes via the `scripts/run_graph.py` entry point.

### 1. CLI (Manual)
Run analysis manually for debugging or ad-hoc checks.

```bash
# Full analysis of specific repos
python scripts/run_graph.py analyze --repos "owner/repo1" "owner/repo2"

# Health check
python scripts/run_graph.py health
```

### 2. Webhook (Event-Driven)
Triggered by GitHub events (Push, PR, Issue).
-   **Payload**: JSON payload from GitHub.
-   **Action**: Thin GitHub App/Action validates signature and forwards to the persistent runner/queue (no LangGraph in CI).

### 3. Dormant Audit (Cron)
Runs every 30 minutes to check for repositories that haven't been updated recently but might need a "heartbeat" check or have missed webhooks.

## 🖥️ Infrastructure

-   **Host**: `zo.computer` (Persistent VM/Container).
-   **Environment**: Dockerized (Postgres, Redis) + Local Runner (Python/Node).
-   **Dependencies**: Managed via `requirements.txt` and `package.json`.
-   **Secrets**: Bitwarden runtime injection for all runs (local, cron/systemd, CI).

## 🔄 Automation Workflow

1.  **Event Ingest**: Webhook received or Cron triggers.
2.  **Queueing/Backpressure**: Job added to queue with dedupe by repo/branch to collapse bursts.
3.  **Pre-Processing**: Node.js script pulls repo and gathers diffs/CI/baseline deltas.
4.  **Orchestration**: LangGraph runner picks up job.
5.  **Execution**: Agents run in parallel.
6.  **Reporting**: Results posted back to GitHub or stored in DB.

## ⚠️ Legacy V1 (Cron Analysis)

*Historical Note*: The V1 system ran as a monolithic 6-hour cron job. This has been superseded by the V2 Event-Driven architecture. The legacy design documents have been archived and removed.
