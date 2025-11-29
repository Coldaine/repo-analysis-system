# Complexity Daemon: Cumulative Auto-Commit

## Overview

A lightweight Python daemon that monitors file changes across repositories, tracks cumulative complexity delta, and automatically commits when a threshold is reached—creating natural, cognitively-sized commit boundaries.

**Location**: `repo-analysis-system/tools/complexity-daemon/`

This is a **local tool** that runs on developer machines, while the main repo-analysis-system runs centrally on zo.computer. They complement each other:
- **complexity-daemon** (local) → creates well-sized commits
- **repo-analysis-system** (central) → analyzes those commits

---

## Problem Statement

Developers often create massive "did 47 things" commits because:
1. No natural stopping point during flow state
2. Arbitrary time-based commits don't match cognitive load
3. Manual discipline fails under deadline pressure

**Solution**: Automatically commit when cumulative complexity exceeds threshold, creating reviewable chunks that match human cognitive capacity.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Developer Machine                                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Complexity Daemon (systemd user service)           │   │
│  │                                                     │   │
│  │  ┌──────────────┐    ┌──────────────────────────┐  │   │
│  │  │   Watcher    │───▶│  Complexity Calculator   │  │   │
│  │  │  (watchdog)  │    │  (lizard/radon)          │  │   │
│  │  └──────────────┘    └──────────────────────────┘  │   │
│  │         │                       │                   │   │
│  │         ▼                       ▼                   │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │           State Store (SQLite)               │  │   │
│  │  │  - Per-file complexity baseline              │  │   │
│  │  │  - Cumulative delta since last commit        │  │   │
│  │  │  - Last commit hash                          │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                      │                              │   │
│  │                      ▼ (threshold exceeded)         │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │           Auto-Commit Engine                 │  │   │
│  │  │  - Stage all changes                         │  │   │
│  │  │  - Generate commit message                   │  │   │
│  │  │  - Reset cumulative counter                  │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Repos:                                                     │
│   ~/projects/app1/  ──┐                                     │
│   ~/projects/app2/  ──┼── Watched by daemon                 │
│   ~/projects/app3/  ──┘                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Model

### Option A: User-Level Systemd Service (Recommended)

```bash
# ~/.config/systemd/user/complexity-daemon.service
[Unit]
Description=Complexity Auto-Commit Daemon
After=default.target

[Service]
Type=simple
ExecStart=/home/%u/.local/bin/cogload
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

**Activation**:
```bash
systemctl --user enable complexity-daemon
systemctl --user start complexity-daemon
```

### Option B: Per-Repo Manual Start

```bash
cogload watch ~/projects/myapp
```

Runs in foreground, monitors single repo. Good for testing.

### Option C: tmux/screen Session

```bash
cogload daemon --config ~/.config/cogload/config.toml
```

Runs all configured repos in background session.

---

## Configuration

### Global Config: `~/.config/cogload/config.toml`

```toml
[daemon]
debounce_seconds = 5          # Wait for rapid changes to settle
poll_interval = 1.0           # File system poll rate (seconds)
log_level = "info"
log_file = "~/.local/share/cogload/daemon.log"

[defaults]
threshold = 50                # Cumulative complexity delta
complexity_tool = "lizard"    # "lizard" | "radon" | "cognitive"
include_patterns = ["*.py", "*.rs", "*.ts", "*.js", "*.go"]
exclude_patterns = ["*_test.py", "test_*.py", "*.spec.ts"]
auto_stage = true             # Stage all changes before commit
message_template = "checkpoint: complexity {delta} (auto)"

[[repos]]
path = "~/projects/coldvox"
enabled = true
# Uses defaults

[[repos]]
path = "~/projects/critical-service"
enabled = true
threshold = 25                # Lower threshold for critical code
exclude_patterns = ["migrations/*.py"]

[[repos]]
path = "~/projects/experimental"
enabled = false               # Disabled, won't be watched
```

### Per-Repo Override: `.cogload.toml` (optional)

```toml
# ~/projects/myapp/.cogload.toml
threshold = 75
exclude_patterns = ["generated/*.py"]
```

---

## Complexity Calculation

### Per-File Delta

```python
def calculate_file_delta(file_path: Path, state_db: StateDB) -> int:
    """
    Calculate complexity change for a single file.
    Returns: positive = more complex, negative = simpler
    """
    current_complexity = lizard.analyze_file(str(file_path))
    total_current = sum(f.cyclomatic_complexity for f in current_complexity.function_list)

    previous = state_db.get_file_complexity(file_path)
    if previous is None:
        # New file - full complexity counts
        return total_current

    delta = total_current - previous
    state_db.set_file_complexity(file_path, total_current)
    return delta
```

### Cumulative Tracking

```python
def on_file_change(event: FileModifiedEvent):
    """Called by watchdog on file modification."""
    file_path = Path(event.src_path)

    # Skip non-tracked files
    if not matches_patterns(file_path, config.include_patterns):
        return
    if matches_patterns(file_path, config.exclude_patterns):
        return

    # Calculate delta
    delta = calculate_file_delta(file_path, state_db)

    # Update cumulative
    cumulative = state_db.get_cumulative_delta()
    cumulative += delta
    state_db.set_cumulative_delta(cumulative)

    log.info(f"{file_path.name}: Δ{delta:+d} → cumulative: {cumulative}")

    # Check threshold
    if cumulative >= config.threshold:
        trigger_auto_commit(cumulative)
```

### Auto-Commit

```python
def trigger_auto_commit(cumulative: int):
    """Stage all changes and commit."""
    repo = git.Repo(config.repo_path)

    # Stage all changes
    repo.git.add('-A')

    # Generate message
    message = config.message_template.format(
        delta=cumulative,
        timestamp=datetime.now().isoformat(),
        files_changed=len(repo.index.diff("HEAD"))
    )

    # Commit
    repo.index.commit(message)

    # Reset counter
    state_db.reset_cumulative_delta()
    state_db.set_last_commit(repo.head.commit.hexsha)

    log.info(f"Auto-committed: {message}")
```

---

## State Database Schema

```sql
-- ~/.local/share/cogload/state.db

CREATE TABLE repos (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    last_commit_hash TEXT,
    cumulative_delta INTEGER DEFAULT 0,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE file_complexities (
    id INTEGER PRIMARY KEY,
    repo_id INTEGER REFERENCES repos(id),
    file_path TEXT NOT NULL,
    complexity INTEGER NOT NULL,
    last_calculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, file_path)
);

CREATE INDEX idx_file_complexities_repo ON file_complexities(repo_id);
```

---

## Edge Cases

### Manual Commit Detection

```python
def check_for_manual_commits():
    """Detect if user committed manually, reset state."""
    repo = git.Repo(config.repo_path)
    current_head = repo.head.commit.hexsha
    stored_head = state_db.get_last_commit()

    if current_head != stored_head:
        log.info("Manual commit detected, resetting cumulative delta")
        state_db.reset_cumulative_delta()
        state_db.set_last_commit(current_head)
        recalculate_baselines()
```

### Branch Switch

```python
def on_branch_change():
    """Handle git branch switch."""
    log.info("Branch changed, recalculating baselines")
    state_db.reset_cumulative_delta()
    recalculate_baselines()
```

### File Deletion

```python
def on_file_deleted(event: FileDeletedEvent):
    """Deleted files reduce cumulative complexity."""
    previous = state_db.get_file_complexity(event.src_path)
    if previous:
        cumulative = state_db.get_cumulative_delta()
        cumulative -= previous  # Negative delta (simpler)
        state_db.set_cumulative_delta(cumulative)
        state_db.delete_file_complexity(event.src_path)
```

---

## CLI Interface

```bash
# Installation (from repo-analysis-system)
pip install -e ".[local-daemon]"
# or standalone
uv tool install cogload

# Commands
cogload init                     # Create default config
cogload add ~/projects/myapp     # Add repo to watch list
cogload remove ~/projects/myapp  # Remove repo
cogload list                     # Show watched repos + status
cogload status                   # Current cumulative delta per repo
cogload watch ~/projects/myapp   # Watch single repo (foreground)
cogload daemon                   # Run daemon for all configured repos
cogload commit                   # Force commit now (manual trigger)
cogload reset                    # Reset cumulative counter
cogload history                  # Show auto-commit history
```

---

## Integration with repo-analysis-system

```
Developer Machine                    zo.computer
┌─────────────────┐                 ┌─────────────────────────┐
│  cogload daemon │                 │  repo-analysis-system   │
│                 │                 │                         │
│  Creates well-  │   git push      │  Analyzes commits       │
│  sized commits  │ ───────────────▶│  created by cogload     │
│                 │                 │                         │
│  (LOCAL tool)   │                 │  (CENTRAL service)      │
└─────────────────┘                 └─────────────────────────┘
```

**The daemon creates commits. The analysis system reviews them.**

---

## Implementation Phases

### Phase 1: Core Library (Week 1)
- [ ] Complexity calculator wrapper (lizard + radon)
- [ ] SQLite state management
- [ ] Git operations (GitPython)
- [ ] Unit tests for delta calculation

### Phase 2: File Watcher (Week 2)
- [ ] watchdog integration
- [ ] Debouncing logic
- [ ] Pattern matching (include/exclude)
- [ ] Manual commit detection

### Phase 3: CLI (Week 3)
- [ ] Click/Typer CLI structure
- [ ] Config file parsing (TOML)
- [ ] Status/list/history commands
- [ ] Single-repo watch mode

### Phase 4: Daemon (Week 4)
- [ ] Multi-repo daemon mode
- [ ] systemd service file
- [ ] Logging and rotation
- [ ] Signal handling (graceful shutdown)

### Phase 5: Polish (Week 5)
- [ ] Installation script
- [ ] Documentation
- [ ] Integration tests
- [ ] Edge case handling

---

## Dependencies

Added to repo-analysis-system's `pyproject.toml`:

```toml
[project.optional-dependencies]
local-daemon = [
    "watchdog>=4.0.0",      # File system monitoring
    "lizard>=1.17.0",       # Complexity analysis
    "gitpython>=3.1.0",     # Git operations
    "typer>=0.12.0",        # CLI framework
    "rich>=13.0.0",         # Pretty output
    "tomli>=2.0.0",         # TOML parsing
]

[project.scripts]
cogload = "tools.complexity_daemon.cli:app"
```

Note: `radon` already exists in base dependencies for the central complexity agent.

---

## Open Questions

1. **Threshold tuning**: What's a good default? 50? 100? Need empirical data.

2. **Commit message AI**: Should we use an LLM to generate meaningful commit messages based on the changes, or keep it simple?

3. **Notification**: Desktop notifications when auto-commit triggers? IDE integration?

4. **Conflict with pre-commit hooks**: If pre-commit modifies files, complexity changes. Handle?

5. **Multi-language support**: Start with Python only, or support Rust/TS/Go from day one?

---

## Relationship to Original Design Doc

The original "Multi-Agent Code Review System" design had the C_LLM daemon triggering the Shadow Council. We've simplified:

| Original Design | Simplified Design |
|-----------------|-------------------|
| C_LLM triggers Shadow Council | cogload triggers auto-commit only |
| Real-time agent review | Agents review on PR (via repo-analysis-system) |
| Complex IDE integration | Simple systemd daemon |
| Immediate feedback loop | Commit-time feedback |

**Why simpler?** The rogue workflow incident showed the danger of over-automated systems. This version creates commits; humans decide when to push/PR.
