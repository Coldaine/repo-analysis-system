# Overview and Goals

**Status**: Canonical
**Last Updated**: November 23, 2025

## 🎯 System Purpose

**The Unified Repository Analysis System** is an intelligent, automated platform that combines continuous PR workflow monitoring with goal-based repository health tracking to provide comprehensive, actionable insights for multi-repository portfolios.

**Core Mission:** Proactively identify repository issues, track progress toward goals, detect plan divergences, and provide automated solutions.

## 🏗️ The 8 Anchor Goals

These goals represent the locked baseline for what this unified system MUST achieve.

### Goal 1: Comprehensive Repository Coverage
**Objective**: Automatically discover, clone, sync, and monitor ALL repositories in the GitHub account(s).
-   **Success Criteria**: 100% coverage, auto-discovery of new repos, graceful handling of deletions.
-   **Mechanism**: GitHub Sync Service (Node.js) + Persistent Repo Cache.

### Goal 2: Locked Baseline Establishment
**Objective**: Establish an immutable "locked baseline" for every repository (goals, phases, tech stack).
-   **Success Criteria**: AI-powered analysis on first encounter, SHA256 hash verification for immutability.
-   **Concept**: The baseline is the "Constitution" of the repo. Any deviation is flagged as "Divergence".

### Goal 3: Proactive PR Workflow Monitoring
**Objective**: Detect stalled PRs, CI/CD failures, and merge conflicts in real-time.
-   **Success Criteria**: Identification of "Pain Points" (e.g., "PR #123 is blocked by missing tests").
-   **Legacy**: This goal inherits the core value proposition of the V1 system.

### Goal 4: Holistic Health Tracking (5 Pillars)
**Objective**: Track health across 5 key dimensions:
1.  **Code Quality**: Complexity, maintainability.
2.  **Documentation**: Completeness, freshness.
3.  **Testing**: Coverage, pass rate.
4.  **Goal Adherence**: Progress vs. Baseline.
5.  **PR Health**: Cycle time, review depth.

### Goal 5: Divergence Detection
**Objective**: Automatically detect when repositories deviate from their locked baseline goals.
-   **Example**: "Baseline says 'No SQL', but `requirements.txt` added `sqlalchemy`."
-   **Action**: The Forensics Agent investigates and flags this as either "Drift" or a "Pivot".

### Goal 6: Efficient Pre-Processing
**Objective**: Gather review items (commits, PRs, issues) deterministically before AI analysis.
-   **Rationale**: "Don't use an LLM to count commits."
-   **Tech**: Node.js scripts for fast I/O and API interaction.

### Goal 7: Parallel Agent Execution
**Objective**: Run analysis concurrently across multiple repositories using LangGraph.
-   **Architecture**: Fan-out/Fan-in pattern.
-   **Scale**: Support for 100+ repositories with controlled concurrency.

### Goal 8: Actionable Reporting
**Objective**: Generate concise, progressive-disclosure status reports (Executive → Detailed).
-   **Format**: Markdown reports with embedded Mermaid visuals.
-   **Delivery**: GitHub Comments, Status Checks, and a future Web Dashboard.

## 🔄 System Flow

```mermaid
graph TD
    A[GitHub Webhook / Cron] --> B[Persistent Runner (zo.computer)]
    B --> C{Event Type?}
    C -->|Push/PR/Issue| D[Pre-Processing (Node.js)]
    C -->|Dormant Audit| E[Dormant Check]
    E -->|Needs Update| D
    D --> F[LangGraph Orchestrator (Python)]
    F --> G[Parallel Analysis Agents]
    G --> H[PostgreSQL (State/Baselines)]
    G --> I[Output Generation]
    I --> J[GitHub Comments / Status Checks]
```

## 👥 Target Audience

-   **Engineering Managers**: For high-level health tracking and goal adherence.
-   **Tech Leads**: For identifying architectural pain points and divergences.
-   **Developers**: For immediate feedback on PRs and automated conflict resolution.

## 🔑 Key Concepts

-   **Locked Baseline**: A read-only record of a repository's intended purpose and goals.
-   **5 Pillars**: The standard metrics for health (Code, Docs, Tests, Goals, PRs).
-   **Progressive Disclosure**: Reports that start with a summary and allow drilling down into details.
-   **Event-Driven**: The system reacts to changes (webhooks) rather than just polling.
