# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The **Repository Analysis System** is a LangGraph-orchestrated platform for automated repository health monitoring, goal tracking, and architectural divergence detection. It uses LLMs to synthesize "Mental Models" (Blueprints) of repositories and audits codebases against documented intent.

**Core Philosophy**: This is an **LLM-First Reasoning** system. Unlike traditional linters that check syntax, this system checks **meaning**. It asks "Based on the history and config, what was the intended architecture?" rather than grepping for specific strings.

## Development Commands

### Environment Setup

```bash
# Install Python dependencies
uv sync

# Note: Node.js dependencies are NOT yet implemented in this repository
# (Pre-processing layer is planned but not built)
```

### Running the System

The primary entry point is `scripts/run_graph.py`. **Always use Bitwarden Secrets Manager** for secrets injection:

```bash
# Full analysis run (with secrets injection)
bws run -- python scripts/run_graph.py analyze --repos "owner/repo"

# Health check
bws run -- python scripts/run_graph.py health

# System statistics
bws run -- python scripts/run_graph.py stats

# Sync repositories locally
bws run -- python scripts/run_graph.py sync --repos "owner/repo1" "owner/repo2"

# Migrate legacy config
python scripts/run_graph.py migrate --legacy-config config.yaml
```

### Analysis Run Options

```bash
# Run types
--run-type full          # Complete analysis (default)
--run-type incremental   # Only analyze changes
--run-type webhook       # Triggered by GitHub webhook

# Enable PR review (disabled by default)
--enable-pr-review

# Override LangGraph recursion limit (default: 25)
--recursion-limit 50

# Select checkpointer (memory or postgres)
--checkpointer postgres
```

### Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_complexity_analyzer.py

# Run specific test
python -m pytest tests/test_complexity_analyzer.py::TestComplexityAnalyzer::test_simple_function_complexity

# Run with verbose output
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Architecture Overview

### Hybrid Stack: Python + Node.js (Planned)

- **Python**: Primary language for LangGraph orchestration and AI agents
- **Node.js**: Planned for pre-processing layer (Git operations, GitHub API, deterministic data gathering)
- **PostgreSQL**: Required backend for concurrent writes and LangGraph checkpointing
- **Bitwarden**: Secrets management (never use `.env` files)

### LangGraph Orchestration

The system uses a **StateGraph** workflow with these key nodes:

1. **initialize** → Create analysis run in database
2. **sync_repositories** → Clone/update local mirrors
3. **detect_changes** → Identify changed repositories
4. **collect_data** → Gather repository metadata
5. **analyze_complexity** → Run Radon complexity analysis
6. **analyze_security** → Scan for vulnerabilities
7. **analyze_repositories** → LLM-based pain point analysis
8. **generate_visualizations** → Create Mermaid diagrams
9. **review_pull_requests** → Optional PR reviews
10. **generate_report** → Produce markdown reports
11. **finalize** → Complete analysis run

See `src/orchestration/graph.py:89-136` for the complete graph definition.

### Agent Catalog

The system uses specialized agents, each with distinct toolboxes:

- **The Archivist (DocCatalog)**: Discovers all "Intent" sources (READMEs, docs, configs)
- **The Architect (PillarExtraction)**: Synthesizes 3-5 core "Architectural Pillars" from intent sources
- **The Auditor (ImplementationValidator)**: Gap analysis between Blueprint and actual code
- **The Decisions Agent (Forensics)**: Resolves conflicts using Git history (blame, log, diff)
- **Complexity Agent**: Radon-based cyclomatic complexity analysis
- **Security Agent**: Vulnerability scanning (Bandit, pattern matching)
- **Visualization Agent**: Mermaid diagram generation
- **Output Agent**: Progressive-disclosure reporting (Levels 1-4)
- **PR Review Agent**: Programmatic PR reviews (disabled by default)

### The "Golden Rule" of Truth

When conflicts arise (README vs Code), apply this hierarchy:

1. **`/docs/` > `README.md`**: Detailed docs outweigh README (which rots)
2. **Pivot > History**: Recent "Refactor" or "Pivot" commits override older documentation
3. **Code > Comments**: Working code is the ultimate reality

## Configuration

### Primary Config: `config/new_config.yaml`

- **Database**: PostgreSQL connection settings (host, port, name, user, pool_size)
- **Models**: GLM-4.6, MiniMax, Ollama endpoints and parameters
- **Orchestration**: LangGraph settings (max_concurrent_runs, timeout, retry_attempts)
- **Agents**: Per-agent configuration (enabled/disabled, model selection, limits)
- **Repositories**: Workspace path, default owner, target repos list

### Secrets Management (Bitwarden Only)

**Never commit secrets to `.env` files.** All secrets must be injected via Bitwarden Secrets Manager:

Required secrets:
- `GITHUB_TOKEN` - API access for cloning and fetching data
- `GITHUB_OWNER` - Default repository owner/namespace
- `GLM_API_KEY` - GLM model access
- `MINIMAX_API_KEY` - MiniMax model access
- `POSTGRES_PASSWORD` - Database password
- `GOOGLE_SEARCH_KEY` - (Optional) Search integration
- `GOOGLE_CX` - (Optional) Google Custom Search Engine ID

Setup: See `docs/operations/Config-and-Secrets.md` for Bitwarden setup guide.

## Database Schema (SQLAlchemy 2.0)

**IMPORTANT**: This project uses **SQLAlchemy 2.0** declarative base import:

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

NOT the legacy `from sqlalchemy.ext.declarative import declarative_base`.

Key models (defined in `src/models/`):
- **Repository**: Tracked repositories with health scores
- **AnalysisRun**: Workflow execution records (status, created_by, completed_at)
- **RepositoryCharter**: Intent/Blueprint snapshots
- **Metrics**: Time-series health metrics

PostgreSQL is **required** - SQLite cannot handle concurrent writes from parallel agents.

## Key File Locations

### Source Code Structure

- `src/agents/` - LangGraph agent implementations
- `src/analysis/` - Complexity analyzer (Radon)
- `src/security/` - Vulnerability scanner
- `src/orchestration/` - LangGraph workflow (`graph.py`)
- `src/models/` - SQLAlchemy models
- `src/storage/` - Database adapter
- `src/preprocessing/` - Change detection and repo sync
- `src/utils/` - Config loader, logging, validation
- `src/repo_manager.py` - Repository synchronization

### Configuration & Docs

- `config/new_config.yaml` - Primary configuration file
- `.env.example` - Template for manual env vars (NOT recommended)
- `docs/` - Canonical documentation (prioritized over README)
- `docs/core-concepts/` - System Architecture, Agents and Workflows
- `docs/operations/` - Runtime, Config, Observability
- `docs/project-info/` - Overview, Implementation Status, Roadmap

### Output & Logs

- `review_logging/` - Agent logs and analysis reports (auto-generated)
- `workspace/repos/` - Local repository mirrors
- `logs/` - System logs

## Common Development Patterns

### Adding a New Agent

1. Create agent file in `src/agents/` extending base patterns
2. Define agent's toolbox (e.g., `read_file`, `git_log`, `grep_search`)
3. Implement agent node function with signature: `async def node_fn(state: GraphState) -> GraphState`
4. Register node in `src/orchestration/graph.py:_build_langgraph()`
5. Add agent configuration to `config/new_config.yaml` under `agents:`
6. Update `docs/core-concepts/Agents-and-Workflows.md` with agent profile

### Model Routing (CCR - Claude Code Router)

The system uses tiered model routing for cost optimization:

- **Claude 3.5 Sonnet / GLM 4.6**: Complex reasoning (Architect, Forensics)
- **Haiku / MiniMax**: Simple tasks (Archivist, summarization)
- **Ollama (Local)**: Privacy-sensitive scans or offline use

Model selection is configured per-agent in `config/new_config.yaml`.

### LangGraph State Management

- **GraphState** is a TypedDict (defined in `src/orchestration/graph.py:35-59`)
- Return **deltas only** from node functions - don't re-emit full lists
- Use reducers for list operations to prevent exponential duplication
- Keep ephemeral/scratch data out of persisted checkpoints

### Checkpointer Selection

Two options available:
1. **MemorySaver** (default) - In-memory, no persistence
2. **PostgresSaver** - Postgres-backed, supports resume/time-travel

Configure via `--checkpointer postgres` or in `config/new_config.yaml`:
```yaml
orchestration:
  langgraph:
    checkpointer: postgres  # or memory
```

## Testing Philosophy

- Unit tests in `tests/` (pytest)
- Test files mirror source structure: `tests/test_<module>.py`
- Use `tempfile.mkdtemp()` for test fixtures requiring file operations
- Mock external dependencies (GitHub API, AI models, database)
- Test coverage should include: happy path, error handling, edge cases

## Important Constraints

### DO NOT:
- Store secrets in `.env` files (use Bitwarden only)
- Use SQLite (PostgreSQL required for concurrent writes)
- Skip the LangGraph orchestration layer
- Grep for architectural decisions (ask the LLM instead)
- Commit credentials, API keys, or tokens
- Use legacy SQLAlchemy imports (`from sqlalchemy.ext.declarative import declarative_base`)

### DO:
- Always run with `bws run --` for secrets injection
- Use structured logging via `src/utils/logging.py`
- Preserve LangGraph state immutability (return deltas)
- Follow the "Golden Rule of Truth" hierarchy for conflict resolution
- Check `docs/` for canonical documentation
- Use correlation IDs for distributed tracing

## Documentation

The canonical documentation is located in `docs/`:

1. [Overview and Goals](docs/project-info/Overview-and-Goals.md)
2. [System Architecture](docs/core-concepts/System-Architecture.md)
3. [Agents and Workflows](docs/core-concepts/Agents-and-Workflows.md)
4. [Runtime and Automation](docs/operations/Runtime-and-Automation.md)
5. [Configuration and Secrets](docs/operations/Config-and-Secrets.md)
6. [Observability and Reporting](docs/operations/Observability-and-Reporting.md)
7. [Implementation Status](docs/project-info/Implementation-Status-and-Roadmap.md)
8. [Templates and Examples](docs/guides/Templates-and-Examples.md)

**When in doubt**: Check `docs/` first (it outweighs README and code comments).
