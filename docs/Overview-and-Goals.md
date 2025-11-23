# Overview and Goals

**Status**: Canonical
**Last Updated**: November 23, 2025

## 🎯 System Purpose

**The Unified Repository Analysis System** is an intelligent, automated platform that combines continuous PR workflow monitoring with goal-based repository health tracking to provide comprehensive, actionable insights for multi-repository portfolios.

**Core Mission:** Proactively identify repository issues, track progress toward goals, detect plan divergences, and provide automated solutions.

## 🚀 High-Level Goals

1.  **Comprehensive Repository Coverage**: Automatically discover, clone, sync, and monitor ALL repositories in the GitHub account(s).
2.  **Locked Baseline Establishment**: Establish an immutable "locked baseline" for every repository (goals, phases, tech stack).
3.  **Proactive PR Workflow Monitoring**: Detect stalled PRs, CI/CD failures, and merge conflicts in real-time.
4.  **Holistic Health Tracking (5 Pillars)**: Track Code Quality, Documentation, Testing, Goal Adherence, and PR Health.
5.  **Divergence Detection**: Automatically detect when repositories deviate from their locked baseline goals.
6.  **Efficient Pre-Processing**: Gather review items (commits, PRs, issues) deterministically before AI analysis.
7.  **Parallel Agent Execution**: Run analysis concurrently across multiple repositories using LangGraph.
8.  **Actionable Reporting**: Generate concise, progressive-disclosure status reports (Executive → Detailed).

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
