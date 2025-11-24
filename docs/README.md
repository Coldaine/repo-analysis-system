# Documentation Index (Canonical)

The live, non-contradictory documentation for the Repo Analysis System.

> Terminology update: We use **Repository Charter** (formerly "baseline") to describe each repo's locked intent/purpose record, and the eight anchors are referred to as the **Goal Framework**. This clarifies that we are preserving goals, not code snapshots.

## 📚 Core Concepts (`core-concepts/`)
Fundamental architecture and patterns for LangGraph v1.0.
- [System Architecture](core-concepts/System-Architecture.md): High-level design, orchestration, and persistence.
- [Agents & Workflows](core-concepts/Agents-and-Workflows.md): Graph definitions, subgraphs, and agent patterns.
- [State Model & Reducers](best-practices-reference.md): `TypedDict` state, `add_messages`, and reducer semantics.
- [ToolNode Patterns](core-concepts/ToolNode-and-Tool-Patterns.md): Scatter-gather, error handling, and tool execution.
- [Runtime Object](core-concepts/Runtime-Object.md): Dependency injection and context management.

## ⚙️ Operations (`operations/`)
Running, configuring, and monitoring the system.
- [Runtime & Automation](operations/Runtime-and-Automation.md): Execution modes (CLI, Webhook, Cron) and infrastructure.
- [Config & Secrets](operations/Config-and-Secrets.md): Configuration management and Bitwarden integration.
- [Observability](operations/Observability-and-Reporting.md): Tracing, logging, and metrics (LangSmith/OTel).
- [Checkpointer & Persistence](operations/Checkpointer-and-Persistence.md): Postgres persistence and time-travel.
- [Bitwarden Secrets Integration](Bitwarden-Secrets-Integration.md): Quick-start checklist for the `bws` CLI and required secrets.

## 📘 Guides (`guides/`)
How-to guides and references.
- [Migration Guide v1.0](guides/Migration-Guide-v1.0.md): Checklist for migrating from v0.x to v1.0.
- [Testing & Validation](guides/Testing-and-Validation.md): Unit and integration testing strategies.
- [Templates & Examples](guides/Templates-and-Examples.md): Code snippets and patterns.

## ℹ️ Project Info (`project-info/`)
Goals, roadmap, and decisions.
- [Overview & Goals](project-info/Overview-and-Goals.md): Project vision and objectives.
- [Status & Roadmap](project-info/Implementation-Status-and-Roadmap.md): Current progress and future plans.
- [Architecture Decisions Index](project-info/UNIFIED-DECISIONS.md): ADR log pointing back to the canonical overview.

## Quick Links
- [Main README](../README.md)
- [Configuration](../config.yaml)
