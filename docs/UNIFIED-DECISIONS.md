# Unified System Architecture - Decisions Log

**Date**: November 17, 2025  
**Status**: LOCKED BASELINE  
**Version**: 1.0

---

## ✅ Finalized Decisions (Big Bang LangGraph Revision)

### Decision 1: Primary Programming Language
**DECISION**: Hybrid (Python Primary + Node.js for Pre-processing)

**Clarification (Revised)**: LangGraph will be adopted **immediately** (Big Bang) rather than phased later. Earlier notes suggesting a Phase I without LangGraph are superseded. We will stand up initial LangGraph graphs early to avoid building throwaway orchestration code.

**Rationale**:
- Reduces duplicate effort (no temporary orchestration layer)
- LangGraph surface area needed is small (few flows / nodes)
- Repositories are largely independent → ideal for LangGraph fan‑out patterns
- Faster path to parallel execution & stateful coordination

**Impacts**:
- LangGraph listed as core dependency in `requirements.txt`
- Early focus on defining graph nodes & state model
- Avoids rework of a temporary sequential orchestrator

---

### Decision 2: Agent Execution Model
**DECISION**: Hybrid by Task targeting eventual pure parallel (LangGraph from start)

**Model**:
- Intra‑repo pipeline remains ordered (PreProcess → DataCollection → Analysis → PainPointDetection → Research → Visualization → Output)
- Inter‑repo execution uses LangGraph fan‑out (one node emits repo list → dynamic subgraph instantiation)
- Backpressure / resource throttling handled via concurrency limits in runner configuration

**Future Path**: If stable, collapse any remaining sequential coordinator logic into fully parallel node scheduling (pure parallel). No interim non‑LangGraph orchestrator.

---

### Decision 3: Scheduling Strategy
**DECISION**: Event-driven (webhook / change detection) with periodic lightweight audit (30m) only to confirm inactivity.

**Mechanism**:
- GitHub webhook (push, PR open/update, issue events) enqueue repositories for graph execution.
- Pre-processing node validates actual delta (skip if empty diff & no new artifacts).
- 30‑minute cron invokes a "Dormant Audit" subgraph: scans for repositories with stale baselines (>X hours) or missed webhook events; triggers only those needing refresh.

**TODO (Design Detail)**:
- Define change signature (commit SHA delta, PR count delta, file diff, CI status change)
- Map event types → which subgraph path executes (full vs partial)
- Concurrency policy for burst events (queue + collapse duplicates)

**Benefits**:
- Zero cost when repos inactive
- Immediate response to changes (via webhooks)
- Fallback prevents missed events

**TODO**: Map each agent's responsibilities and triggers
- Which agents run on which events?
- What constitutes a "change" requiring analysis?
- Detailed trigger logic per agent type

---

### Decision 4: State Management Approach
**DECISION**: Hybrid with Proper Database Selection

**Requirement**: Choose database that meets actual needs, not just default to SQLite

**Database Selection Criteria**:
- Support for concurrent writes (parallel agents)
- JSON/structured data storage
- Query performance for historical analysis
- Version control/audit trail capabilities
- Deployment simplicity (self-hosted on zo.computer)

**Candidates to Evaluate**:
- **PostgreSQL**: Full-featured, excellent for structured data, JSON support
- **SQLite**: Simple, but limited concurrency
- **MongoDB**: Good for flexible schemas, JSON-native
- **DuckDB**: Analytics-optimized, embedded
- **SurrealDB**: Multi-model, modern features

**TODO**: Detailed database requirements analysis
- Concurrent write patterns
- Query patterns (time-series? aggregations?)
- Data volume estimates
- Backup/recovery needs

**Storage Layers** (Confirmed):
- **Database**: Baselines, metrics, state (structured queries)
- **JSON Files**: Configuration (version-controlled)
- **Markdown**: Analysis logs (human-readable history)

---

### Decision 5: Primary System Focus
**DECISION**: Equal Weight - Both PR Monitoring AND Goal Tracking

**Key Clarification**: Cost is NOT a constraint
- "Higher cost is not a problem or an anti-goal"
- No need to compromise features for cost savings
- Both capabilities provide value
- No inherent conflict between the two goals

**Implementation**:
- **PR Workflow Monitoring**: Real-time, event-driven
- **Goal/Baseline Tracking**: Periodic assessment
- Both run in parallel (different agent types)
- Comprehensive repository intelligence

**Feature Parity**:
- Full Vision 1 capabilities (PR pain points)
- Full Vision 2 capabilities (baseline adherence)
- No phasing or compromise needed

---

### Decision 6: Model Selection & Orchestration Strategy
**DECISION (Revised)**: Immediate LangGraph + CCR; phased model breadth (start with CCR Claude → expand to GLM/MiniMax/Ollama once orchestration stable).

**Initial (Big Bang)**:
- LangGraph manages graph & state.
- CCR → Claude (single provider) keeps surface small.

**Expansion Trigger**: After baseline stability metrics (error rate <2%, avg run time acceptable) add multi‑model routing node.

**Routing Plan**:
- Claude: general analysis & summarization
- GLM 4.6: deeper semantic / pattern scoring
- MiniMax: quick triage nodes (fast classification branches)
- Ollama: privacy-sensitive repository scans

**Why**: Avoid temporary orchestration layer; concentrate complexity where it scales.

---

### Decision 7: Baseline System Implementation
**DECISION**: Full Baseline System immediately (LangGraph node: `initialize_or_load_baseline`). Effort acceptable; no interim simplified mode.

**Implementation** (Vision 2 Complete Design):
- ✅ Repository initialization with AI analysis
- ✅ Locked baselines stored in database
- ✅ SHA256 verification for immutability
- ✅ 4-10 goals per repository with success criteria
- ✅ Development phases with milestones
- ✅ Divergence detection from baseline
- ✅ Classification (greenfield, legacy, migration, etc.)
- ✅ Technology stack tracking

**No Phasing**: Build it properly from the start
- Full structure as designed in Vision 2
- Repository Initialization Template as spec
- Complete baseline management system

---

### Decision 8: Pre-Processing Implementation
**DECISION**: Hybrid (Option D) implemented as first node set: `detect_changes` → conditional edge (skip vs proceed) → `gather_deterministic_artifacts`.

**Key Insight**: "Some stuff is trivial to pre-process, some requires AI"

**Deterministic Pre-Processing** (Scripts with GitHub token):
- ✅ New commits since last run
- ✅ Pull request changes
- ✅ Issue updates
- ✅ File diffs
- ✅ Merge conflict detection
- ✅ CI/CD status changes
- ✅ Dependency updates
- ✅ Configuration changes

**Requires AI** (Agent analysis):
- ❌ Pain pattern identification (needs semantic understanding)
- ❌ Solution recommendations (requires reasoning)
- ❌ Code quality assessment (needs context)
- ❌ Goal divergence interpretation (requires judgment)

**Implementation**:
- Node.js pre-processing scripts gather all deterministic data
- Output structured JSON for agent consumption
- Agents focus on analysis and reasoning tasks
- Clear separation of concerns

---

### Decision 9: Repository Discovery & Sync
**DECISION**: Hybrid (Auto personal; Manual orgs). LangGraph kickoff node `sync_repositories` runs periodically (12h) outside normal change-driven path.

---

### Decision 10: Output Format & Verbosity
**DECISION**: Progressive Disclosure + Template Approval. Output nodes: `emit_summary`, `emit_visuals`, `emit_detailed_report` (conditional on config), `emit_raw_artifacts` (archival path).

**Key Process**: 
1. Create template report for each report type
2. Apply template to ONE example repository
3. Review and approve the format
4. Use approved format going forward

**Progressive Disclosure Levels**:
- **Level 1**: Executive summary
- **Level 2**: Visualizations
- **Level 3**: Detailed analysis
- **Level 4**: Raw data

**Template-Driven**:
- Define report templates
- Test on real repository
- Iterate until approved
- Lock template format
- Generate consistently

---

### Decision 11: Secrets Management Strategy
**DECISION**: Bitwarden Secrets Manager with Runtime Injection (No Files)

**Implementation**:
- **Tool**: Bitwarden Secrets Manager (`bws` CLI)
- **Method**: Runtime injection via `bws run` command
- **Storage**: Centralized in Bitwarden cloud (encrypted)
- **Access**: Machine accounts with project-scoped permissions
- **Deployment**: Consistent across local, cron, and CI/CD

**Architecture**:
- Local: `bws run -- python agentic_prototype.py`
- Cron/Systemd: Wrapper script with `bws run`
- GitHub Actions: `bitwarden/sm-action@v1` official action
- Secrets never written to disk (ephemeral)
- Automatic secret rotation propagation

**Secrets Required**:
- `GITHUB_TOKEN` - GitHub API access
- `GITHUB_OWNER` - Default repository owner
- `GLM_API_KEY` - GLM 4.6 AI model
- `MINIMAX_API_KEY` - MiniMax AI model
- `GOOGLE_SEARCH_KEY` - Google Custom Search API
- `GOOGLE_CX` - Google Search Engine ID

**Benefits**:
- Zero code changes required (transparent to application)
- Automatic audit trail via machine account logs
- Single source of truth for all environments
- Easy secret rotation (update once, applies everywhere)
- GitHub Actions native integration with secret masking
- Prevents secrets in shell history, logs, or process lists

**Implementation Status**:
- Documentation: ✅ Complete (see `docs/Bitwarden-Secrets-Integration.md`)
- Code changes: ✅ None required (already uses env vars)
- Migration: ⏳ Pending manual Bitwarden setup

**Reference**: See detailed implementation guide in `docs/Bitwarden-Secrets-Integration.md`

---

## 🎯 Critical TODOs Before Implementation (Updated for Big Bang)

### 1. Scheduling Strategy Detail (Decision 3)
- [ ] Map each agent type to trigger conditions
- [ ] Define "change" detection logic
- [ ] Specify webhook vs polling strategy
- [ ] Document event-driven architecture

### 2. Database Selection (Decision 4)
- [ ] Define concurrent write requirements
- [ ] Analyze query patterns
- [ ] Estimate data volumes
- [ ] Select specific database technology
- [ ] Design schema

### 3. Report Template Creation (Decision 10)
- [ ] Identify all report types needed
- [ ] Create template for each type
- [ ] Select example repository for testing
- [ ] Generate sample reports
- [ ] Review and approve formats

### 4. Secrets Management Setup (Decision 11)
- [ ] Install Bitwarden Secrets Manager CLI (`bws`)
- [ ] Create "Repo Analysis System" project in Bitwarden
- [ ] Create machine account and generate access token
- [ ] Migrate all 6 secrets to Bitwarden project
- [ ] Configure local development with `bws run`
- [ ] Update cron/scheduled tasks with bws wrapper
- [ ] Setup GitHub Actions with `bitwarden/sm-action@v1`
- [ ] Test secret injection in all environments
- [ ] Remove old environment variable configurations

---

## 📋 Implementation Phases

### Implementation Approach (Revised: Single Big Bang Phase + Enhancement Loop)

**Initial Release Includes**:
- LangGraph orchestration
- Single-model (CCR Claude) usage
- Full baseline system
- Hybrid pre-processing pipeline
- Parallel repo fan-out
- Progressive disclosure outputs

**Post-Release Enhancement Loop**:
1. Add multi-model routing nodes
2. Introduce adaptive scheduling heuristics
3. Performance tuning (parallelism limits, caching)
4. Add anomaly detection subgraph
5. Integrate advanced visualization selection agent

---

## 🔄 Evolution Path (Revised)

**Current State**: Two visions separated → unified big bang plan.
**Next**: Implement LangGraph graph & minimal Claude nodes.
**Then**: Layer model diversification & optimization metrics.
**Vision**: Single cohesive parallel intelligence platform.

---

## Key Philosophy Shifts

1. **Cost is not a constraint** - Build the right system, not the cheap system
2. **Full features from start** - No "lightweight" compromises (e.g., baselines)
3. **Smart pre-processing** - Do what's deterministic, AI does what requires reasoning
4. **Template-driven outputs** - Approve once, generate consistently
5. **Event-driven architecture** - No work when no changes (efficiency without compromise)

---

*This document supersedes earlier phased orchestration notes. Changes require explicit approval and documentation.*
