# Repository Analysis System

## Overview

The **Repository Analysis System** is an intelligent, automated platform for monitoring repository health, tracking goals, and detecting architectural divergences across multi-repository portfolios. It uses **LangGraph** for orchestration, **PostgreSQL** for state management, and **Bitwarden** for secure secrets injection.

## 📚 Documentation

The canonical documentation is located in the `docs/` directory:

1.  [**Overview and Goals**](docs/project-info/Overview-and-Goals.md): High-level purpose, goals, and flows.
2.  [**System Architecture**](docs/core-concepts/System-Architecture.md): Core components, LangGraph design, and execution model.
3.  [**Agents and Workflows**](docs/core-concepts/Agents-and-Workflows.md): Catalog of agents (Forensics, Security, etc.) and their interactions.
4.  [**Runtime and Automation**](docs/operations/Runtime-and-Automation.md): How to run the system (CLI, Webhook, Cron).
5.  [**Configuration and Secrets**](docs/operations/Config-and-Secrets.md): Config schema and Bitwarden setup.
6.  [**Observability and Reporting**](docs/operations/Observability-and-Reporting.md): Logging, metrics, and report formats.
7.  [**Implementation Status**](docs/project-info/Implementation-Status-and-Roadmap.md): Current feature status and roadmap.
8.  [**Templates and Examples**](docs/guides/Templates-and-Examples.md): Standard templates for Repository Charter records, reports, and comparisons.

## 🚀 Quick Start

### Prerequisites

-   Python 3.10+
-   Node.js 18+
-   PostgreSQL 14+
-   Bitwarden Secrets Manager CLI (`bws`)

### Installation

```bash
# Install Python dependencies
uv sync

# Install Node.js dependencies (for pre-processing)
npm install
```

### Running Analysis

```bash
# Run with Bitwarden secrets injection
bws run -- python scripts/run_graph.py analyze --repos "owner/repo"
```

See [Runtime and Automation](docs/operations/Runtime-and-Automation.md) for more details.

## 📁 Project Structure

-   `src/`: Source code (Agents, Orchestration, Models).
-   `docs/`: Canonical documentation.
-   `archive/`: Historical documents and legacy code.
