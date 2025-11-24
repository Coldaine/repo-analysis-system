# Implementation Status and Roadmap

**Status**: Canonical
**Last Updated**: November 23, 2025

## ✅ Completed
-   **Core Architecture**: LangGraph orchestration scaffolding with PostgreSQL persistence.
-   **Secrets**: Bitwarden runtime injection (`bws run`) fully documented and integrated.
-   **Database**: PostgreSQL adapter and schema for Repository Charters / metrics.
-   **Agents**: Data Collection, Complexity, and Security agents scaffolded.
-   **Documentation**: Consolidated into 8 canonical files; legacy archives cleaned.

## 🚧 In Progress / Gaps
-   **Ingest Layer**: Webhook/App ingress + Redis queue/backpressure not implemented.
-   **Pre-Processing**: Deterministic Node.js pipeline not implemented.
-   **Repository Charter System**: Schema exists, but initialization/loading logic is missing.
-   **Divergence Detection**: Logic to compare current state vs. locked Repository Charter is missing.
-   **Forensics Sub-Graph**: Needs full implementation of the "Pattern B" functional wrapper.
-   **Reporting**: Template approval and GitHub publishing workflow incomplete.

## 📊 Feature Status Matrix

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Webhook Ingress** | 🔴 Not Started | Needs thin App/Action + Redis Queue |
| **Dormant Audit** | 🟡 Planned | Cron job to trigger stale repos every 30m |
| **Pre-Processing (Node)** | 🔴 Not Started | Must gather git/PR/issues/CI/charter deltas |
| **Repository Charter Init/Load** | 🟡 Partial | Schema exists; logic missing |
| **Divergence Detection** | 🔴 Not Started | Needs intent compare + routing |
| **Forensics Agent** | 🟡 Partial | Scaffolded; needs Sub-Graph implementation |
| **PR Review Agent** | 🟡 Partial | Writes logs; commenting disabled by default |
| **Parallelism** | 🟢 Supported | LangGraph supports it; ingress controls missing |
| **Secrets** | 🟢 Complete | Bitwarden runtime injection documented |

## 📅 Roadmap (Aligned to Anchor Goals)

### Phase 1: Stabilization & Core Plumbing (Current)
**Goal**: Get the "Skeleton" walking.
1.  **Ingest**: Implement the Redis Queue and the thin GitHub Action forwarder.
2.  **Pre-Processing**: Build the Node.js script to generate the `RepoContext` JSON.
3.  **Repository Charter**: Implement the charter initializer node (`initialize_or_load_baseline` is the current legacy name for the Repository Charter loader).
4.  **Forensics**: Implement the Investigator Sub-Graph using LangGraph v1.0 patterns.

### Phase 2: Monitoring & Reporting (Q1 2026)
**Goal**: Make it useful for developers.
1.  **PR Review**: Wire up the agent to post comments (optional) and status checks.
2.  **Divergence**: Implement the logic to flag "Drift" vs. "Pivot".
3.  **Reporting**: Finalize the progressive disclosure templates (Level 1–3).

### Phase 3: Optimization & Scale (Q2 2026)
**Goal**: Run on 100+ repos cost-effectively.
1.  **Model Routing**: Expand CCR to use GLM/MiniMax/Ollama for cost savings.
2.  **Dashboard**: Build a web UI on top of the PostgreSQL metrics.
3.  **Performance**: Optimize the Node.js git operations and LangGraph concurrency.

## 🛠️ Technical Debt / Refactoring
-   **LangGraph Upgrade**: Ensure we are using the latest v1.0 patterns (Runtime Object, ToolNode).
-   **Testing**: Increase unit test coverage for individual agents.
