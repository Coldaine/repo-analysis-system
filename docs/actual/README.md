# Actual Docs Index

This folder is the curated, non-contradictory reference for the current architecture and implementation. It aligns with `docs/UNIFIED-DECISIONS.md` and the updated `docs/vision-v2-parallel-agents/Implementation-Anchor-Goals.md`.

- **Canon**
  - `../UNIFIED-DECISIONS.md` — architecture, scheduling, secrets, outputs.
  - `../vision-v2-parallel-agents/Implementation-Anchor-Goals.md` — goals and success criteria, aligned to LangGraph + PostgreSQL + Bitwarden.
- **Config & Secrets**
  - `Config-and-Secrets.md` — Bitwarden runtime injection, config schema pointers.
- **Implementation**
  - `implementation-guide.md` — LangGraph v1.0 patterns, subgraph isolation, ToolNode usage, runtime/context guidance.
- **Operations**
  - `../Bitwarden-Secrets-Integration.md` (use only the runtime injection guidance; cron snippets are superseded by webhook + dormant-audit scheduling).

Historical/legacy material (vision v1/v2, synthesis, old plans) is kept outside this folder for reference only.***
