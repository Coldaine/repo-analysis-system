# Overview and Goals

**Status**: Canonical  
**Last Updated**: November 23, 2025

This document fuses the former "Overview", "Implementation Anchor", and "Unified Decisions" narratives into one layered reference. It explains _why_ the unified system exists, _what_ success looks like (the eight locked goals, collectively called the Goal Framework), and _how_ those goals stay protected over time.

## 🎯 System Mission

The **Unified Repository Analysis System** combines deterministic pre-processing with LangGraph-based agents to deliver continuous PR workflow monitoring, goal adherence tracking, and progressive reports across an entire GitHub portfolio.

**Core mandate:** discover every repository, record an immutable Repository Charter, detect divergences in real time, and provide actionable remediation guidance without human babysitting.

> **Terminology note**: Historical references to a "locked baseline" now use **Repository Charter** (or "Intent Record") to emphasize that we are preserving the repo's purpose, not a code snapshot. The eight-goal structure is referred to as the **Goal Framework**.

## 💡 Value Proposition

- **Full Coverage** – Auto-syncs every repo and never trusts stale READMEs again.
- **Intent vs. Reality** – Extracts architectural pillars, compares them against code, and flags drift.
- **Parallel Intelligence** – Fans out specialized agents (Archivist, Architect, Forensics, Complexity, Security, Output) with shared state.
- **Progressive Disclosure** – Produces executive summaries, visuals, detailed findings, and raw artifacts in a consistent template.

## 🧱 Anchor Goals (Summary)

| # | Goal | Objective | Key Deliverables | Status |
|---|------|-----------|------------------|--------|
| 1 | Comprehensive Coverage | Auto-discover, clone, and sync 100% of repos. | GitHub Sync Service, repo cache health dashboard. | 👷 In progress |
| 2 | Repository Charter Program | Capture immutable goals/phases/tech stack per repo. | Charter analyzer, SHA256 verification, Postgres storage. | 👷 In progress |
| 3 | PR Workflow Monitoring | Detect stalled PRs, CI failures, merge conflicts. | PR health agent, pain-point heuristics, notification hooks. | 🟡 Legacy features porting |
| 4 | 5-Pillar Health Tracking | Score code, docs, tests, adherence, PR health. | Pillar scoring framework, historical trending. | 🟡 Designing |
| 5 | Divergence Detection | Compare live repos vs. locked Repository Charter and classify drift vs. pivot. | Intent comparison engine, human review queue. | 🔴 Not started |
| 6 | Deterministic Pre-Processing | Gather commits/PRs/issues/diffs before invoking AI. | Node.js gatherer, RepoContext schema. | 👷 In progress |
| 7 | Parallel Agent Execution | Run many repos concurrently with guardrails. | LangGraph fan-out, queue/backpressure policy. | 🟢 Supported |
| 8 | Actionable Reporting | Generate concise, progressive-disclosure reports with visuals. | Markdown templates, Mermaid visualizer, GitHub publishing flow. | 🟡 Templates approved |

## Goal Deep Dive

### Goal 1 – Comprehensive Repository Coverage
**Owner:** GitHub Sync Service.  
**Success Criteria:** 100% repos cloned, pruned when deleted, rate-limit aware, status dashboard.  
**Why it matters:** Every downstream capability depends on accurate local mirrors.

### Goal 2 – Repository Charter Establishment
**Owner:** Repository Initialization System.  
**Definition:** First encounter with a repo triggers AI analysis that records goals, phases, tech stack, and context. Repository Charters are hashed, read-only, and stored in PostgreSQL.  
**Change process:** Updating a Charter requires an explicit "pivot" ADR.

### Goal 3 – Proactive PR Workflow Monitoring
**Owner:** PR Health Pillar (ported from v1).  
**Scope:** Detect stalled PRs (>5 days), CI failures, merge conflicts, missing automation, and suggest fixes.

### Goal 4 – 5 Pillar Health Tracking
**Owner:** Analysis Framework.  
**Metrics:** Code Quality, Documentation, Testing, Goal Adherence, PR Health. Each includes scoring + trend direction.

### Goal 5 – Divergence Detection & Alerting
**Owner:** Intent Comparison Engine.  
**Outcome:** Flag changes that contradict the locked Repository Charter (e.g., architecture shifts, missed milestones). Severity determines whether auto-ack or human review is required.

### Goal 6 – Intelligent Pre-Processing
**Owner:** Node.js Deterministic Gatherer.  
**Promise:** “Don’t waste tokens counting commits.” Collect commits/PRs/issues/diffs/dependency updates before any agent runs.

### Goal 7 – True Parallel Execution
**Owner:** CCR Agent Spawner.  
**Definition:** Configurable `max_concurrent_runs`, queue dedupe, per-repo backpressure, and clean process lifecycle management.

### Goal 8 – Actionable Reporting
**Owner:** Output Agent.  
**Deliverables:** Executive summary, visuals, deep dive, raw artifacts—each derived from approved templates and optionally posted back to GitHub.

## Execution Roadmap

- **Phase 1 (Foundation)** – Coverage, Repository Charters, pre-processing, LangGraph fan-out. (Ref: `docs/project-info/Implementation-Status-and-Roadmap.md`)
- **Phase 2 (Intelligence)** – PR monitoring, 5 pillars, divergence engine, report publication.
- **Phase 3 (Optimization)** – Cost-aware model routing, dashboards, performance tuning.

Progress against each item is tracked in the roadmap document; this overview simply encodes the locked intent.

## Decision Snapshot

Key architecture decisions remain immutable unless superseded via ADR (see `docs/project-info/UNIFIED-DECISIONS.md`). Highlights:

1. **Hybrid Stack (Decision 1)** – Python + LangGraph for orchestration, Node.js for deterministic data gathering. No interim sequential runner.
2. **Event-Driven Scheduling (Decision 3)** – Webhooks first, 30-minute dormant audit fallback, persistent runner on `zo.computer` split from GitHub infrastructure.
3. **Repository Charter System Now (Decision 7)** – No phased MVP; full charter capture, hashing, and divergence handling are mandatory from day one.
4. **Bitwarden Secrets (Decision 11)** – Secrets injected via `bws run`/`bitwarden/sm-action@v1`; no `.env` files allowed.
5. **Progressive Disclosure Outputs (Decision 10)** – Reports always follow Level 1→4 layering with approved templates before automation publishes anything.

Refer to the ADR index for the full log, links, and rationale.

## Change Management & Governance

- **Repository Charter** – When a repo’s intent genuinely changes, raise an ADR, re-run the initialization analysis, and store the new hash. Silent drift is treated as a divergence.
- **Goal Updates** – Changes to the eight anchor goals require consensus across product + platform leads and a documented ADR update.
- **Templates** – Output and report templates live under `docs/guides/Templates-and-Examples.md`; any edits require approval from the Output Agent owner.

Maintaining this document as the single source of truth prevents conflicting directives from creeping back into the project.
