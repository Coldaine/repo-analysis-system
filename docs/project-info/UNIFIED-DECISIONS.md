# Unified System Architecture – ADR Index

**Status**: LOCKED REPOSITORY CHARTER *(legacy “baseline” concept)*  
**Last Reviewed**: November 23, 2025

This file now serves as a lightweight architecture decision record (ADR) index. Detailed narratives live in `docs/project-info/Overview-and-Goals.md`; each entry below summarizes the locked decision and links back to the relevant section.

| ADR | Title | Summary | Decision Date | Reference |
|-----|-------|---------|---------------|-----------|
| 1 | Hybrid Stack (Python + Node.js) | Adopt LangGraph immediately for orchestration while Node.js handles deterministic git/GitHub ingestion. No interim sequential runner. | 2025‑11‑17 | Overview §Decision Snapshot #1 |
| 2 | Agent Execution Model | Intra-repo flow remains ordered, inter-repo runs fan out via LangGraph with backpressure on the runner. | 2025‑11‑17 | Overview §Decision Snapshot #1–2 |
| 3 | Event-Driven Scheduling | GitHub webhooks enqueue jobs; 30m dormant audit fills gaps. GitHub layer stays stateless; persistent runner handles secrets + queue. | 2025‑11‑23 | Overview §Decision Snapshot #2 |
| 4 | Persistence Backend | PostgreSQL is the mandatory checkpointer + state store; no SQLite in production. | 2025‑11‑17 | Checkpointer doc + Overview §Decision Snapshot |
| 5 | Dual Focus (PR + Charter) | Treat PR workflow monitoring and goal tracking as equal priorities; no cost-driven trade-offs. | 2025‑11‑17 | Overview §System Mission |
| 6 | Model Routing Strategy | Start with CCR→Claude, expand to GLM/MiniMax/Ollama once orchestration stability <2% error. | 2025‑11‑18 | Overview §Decision Snapshot |
| 7 | Repository Charter System Now | Build the full intent/charter analyzer (hashing, divergence detection) from day one; no MVP shortcuts. | 2025‑11‑18 | Overview §Goal 2 |
| 8 | Deterministic Pre-Processing | Node.js gatherer collects commits/PRs/issues/diffs before LLMs run; RepoContext JSON is the contract. | 2025‑11‑18 | Overview §Goal 6 |
| 9 | Repository Sync Cadence | Auto-sync personal repos; allow curated org lists. `sync_repositories` node runs every 12h outside main flow. | 2025‑11‑19 | Overview §Goal 1 |
|10 | Progressive Disclosure Outputs | Reports always follow Levels 1→4 using approved templates before publication. | 2025‑11‑19 | Overview §Goal 8 + Templates guide |
|11 | Bitwarden Secrets Everywhere | `bws run`/`bitwarden/sm-action@v1` provide all secrets; `.env` files are forbidden. | 2025‑11‑20 | Config & Secrets doc |
|12 | Split Runner Architecture | GitHub layer only forwards events; the long-lived runner (zo.computer) executes analysis, manages queue/backpressure, and publishes results. | 2025‑11‑23 | Runtime & Automation §Infrastructure |

### How to Add a New Decision
1. Draft the change in an RFC or PR and socialize it with the platform + product leads.
2. Update the relevant canonical doc (usually `Overview-and-Goals.md` or an operations guide).
3. Append a new row to this table with the ADR number, summary, and reference anchor.
4. Mention the ADR in the weekly status report so downstream agents know that intent changed.

### Change Control Checklist
- If a decision replaces an earlier one, mark the obsolete row as “Superseded by ADR-X” in the summary column.
- Keep summaries short; the detailed rationale belongs in the linked document.
- Do not remove historical rows—use the index to show evolution over time.

Maintaining this index keeps architecture intent synchronized with the consolidated overview and prevents conflicting instructions from resurfacing.
4. **Template-driven outputs** - Approve once, generate consistently
5. **Event-driven architecture** - No work when no changes (efficiency without compromise)

---

## Execution Guardrails (Clarification)

- **Event triggers & backpressure**: Webhook-first for push, pull_request (open/update/synchronize/reopen), issues, and CI status/check runs, plus a 30-minute dormant audit cron. Define change signatures, map triggers → subgraphs/run types, collapse duplicate events per repo/branch within a short window, and enforce concurrency limits/queues to prevent burst fan-out.
- **Deterministic pre-processing first**: The Node.js layer gathers commits since last run, file diffs, PR/issue metadata, CI status changes, dependency/config deltas, merge conflicts, and Repository Charter divergences before any LangGraph/LLM calls. PR-only diff ingestion is insufficient; the pre-processing JSON is the contract for downstream agents.
- **Persistent runtime boundaries**: LangGraph executes on a persistent service with PostgreSQL and a repo cache at `repositories.workspace_path`. Transient CI/Action runners must only validate webhooks and forward jobs to the persistent service; they do not run the graph. Queue/backoff live in the persistent tier, not in Actions.
- **Repository Charter and outputs are mandatory**: The full charter system runs on every qualifying repo (no lightweight mode). Progressive disclosure templates (Levels 1–4) must be produced and approved; PR comments/status checks should link to these outputs rather than emit raw model text.
- **Secrets and tokens**: Bitwarden runtime injection (`bws run` / `bitwarden/sm-action@v1`) is the only path for DB/API/LLM credentials. Actions receive only short-lived tokens to call the persistent service; no stored env files or long-lived secrets in runners.

**Implementation Note (LangGraph Runtime Object)**: The Bitwarden runtime injection above is about secrets and run-time environment configuration. It does not automatically imply adoption of the LangGraph `Runtime` object pattern that v1.0 recommends for typed context and store access at node level. The current codebase uses a `config` dictionary and class-level injection; the recommended next-step is to migrate towards creating and passing a LangGraph `Runtime` instance to node invocations to improve type-safety, tracing, and observability.

---

*This document supersedes earlier phased orchestration notes. Changes require explicit approval and documentation.*
