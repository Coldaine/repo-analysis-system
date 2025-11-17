---
title: Architecture Visualization Prompt
purpose: Guide agent to create comprehensive Mermaid diagrams of existing + new system
date: 2025-11-17
---

# Prompt for Architecture Visualization Agent

## 🎯 Your Task

You have access to all documentation in the `repo-analysis-system` repository. Your task is to create comprehensive Mermaid diagrams that visualize:

1. **What currently exists** (the system as documented in Nov 13 files)
2. **What we're adding** (the new components from Nov 17 designs)
3. **How they integrate** (the unified system architecture)

Create **multiple views** to show different perspectives of the system.

---

## 📚 Context Files You Should Review

### Existing System Documentation (Nov 13):
- `docs/automated-cron-analysis-system-design.md` - Core architecture
- `docs/complete-prototype-overview.md` - Implementation details
- `docs/proposed-needs.md` - Requirements and features
- `docs/current-analysis-summary.md` - Current state
- `docs/visual-timeline-proposals.md` - Visualization strategy
- `docs/progress-visuals-corpus.md` - Visual examples

### New System Documentation (Nov 17):
- `docs/Multi-Repo-Agent-Manager-Architecture.md` - New architecture
- `docs/Repository-Initialization-Template.md` - Baseline system
- `docs/Status-Report-Template.md` - Reporting structure
- `docs/Pre-Processing-Script-Design.md` - Efficiency layer

### Synthesis:
- `docs/Synthesis-Analysis.md` - How they merge together

---

## 📊 Required Diagrams

### Diagram 1: Existing System - Conceptual Architecture

Create a Mermaid flowchart showing:
- **Cron Scheduler** (triggers every 6 hours)
- **CCR Orchestrator** (agent chaining)
- **Data Collection Agent** (GitHub API)
- **Analysis Agent** (GLM 4.6, MiniMax, Ollama)
- **Search Agent** (internet research)
- **Visualization Agent** (Mermaid generation)
- **Output Agent** (review_logging updates)
- **Data flows** between components
- **Model usage** at each stage

**Requirements:**
- Show the sequential flow (cron → data → analysis → search → visual → output)
- Highlight which models are used where
- Indicate data sources (GitHub API, internet search)
- Show outputs (review_logging files, visualizations)

---

### Diagram 2: New System - Conceptual Architecture

Create a Mermaid flowchart showing:
- **GitHub Sync Service** (repository monitoring)
- **Repository Monitor** (metadata tracking)
- **CCR Agent Spawner** (parallel Claude instances)
- **Report Generator** (status reports)
- **Scheduler Service** (periodic execution)
- **Baseline Database** (SQLite with locked goals)
- **Pre-Processing Engine** (review item gathering)
- **Data flows** between components
- **Parallel agent execution** (multiple Claude processes)

**Requirements:**
- Show the parallel agent spawning (not sequential chaining)
- Highlight the pre-processing optimization
- Show baseline database integration
- Indicate CCR routing to Z.ai for cost savings
- Show 4 Pillars tracking

---

### Diagram 3: Unified System - High-Level Architecture

Create a Mermaid C4 Context or flowchart showing:
- **External Systems** (GitHub API, Z.ai via CCR, SQLite DB)
- **Main Components** (from both systems, merged)
- **Data Flows** (how information moves through the system)
- **Scheduling** (dual-frequency: 30m quick / 6h deep)
- **Output Artifacts** (reports, visualizations, baseline records)

**Requirements:**
- Show how existing and new components integrate
- Highlight shared infrastructure (CCR, GitHub API)
- Show both monitoring (existing) and baseline tracking (new)
- Indicate cost optimization through CCR routing

---

### Diagram 4: Data Flow - End-to-End

Create a Mermaid sequence diagram showing:
- **User/System** initiates periodic run
- **Scheduler** triggers execution
- **Pre-Processing** gathers review items
- **GitHub Sync** updates repository list
- **Parallel Agents** spawn for analysis
- **Baseline Comparison** detects divergences
- **PR Pain Detection** identifies workflow issues
- **Report Generation** creates outputs
- **Database Updates** stores baseline data
- **File Outputs** writes reports

**Requirements:**
- Show temporal sequence of operations
- Highlight parallel vs. sequential operations
- Show data transformations at each step
- Indicate which components come from existing vs. new system

---

### Diagram 5: Component Integration - Detailed

Create a Mermaid graph showing:
- **All major components** (boxes)
- **Dependencies** between components (arrows)
- **Data stores** (databases, files)
- **External APIs** (GitHub, Z.ai, internet search)
- **Color coding**:
  - Green = Existing system components
  - Blue = New system components
  - Purple = Shared/Unified components

**Requirements:**
- Show every component from both systems
- Clearly mark which are being added vs. which exist
- Show shared infrastructure
- Indicate data persistence points

---

### Diagram 6: 5 Pillars Framework

Create a Mermaid mindmap or flowchart showing:
- **5 Pillars** of the unified system:
  1. Code Quality (new)
  2. Documentation (new)
  3. Testing (new)
  4. Adherence to Plan (new)
  5. PR Health (from existing)
- **Metrics** tracked under each pillar
- **Data sources** for each pillar
- **How existing pain point detection feeds into pillars**

**Requirements:**
- Show how PR Health pillar integrates existing system's focus
- Show baseline tracking for Adherence to Plan
- Indicate which agents analyze which pillars

---

### Diagram 7: Scheduling & Execution Flow

Create a Mermaid Gantt chart or timeline showing:
- **Quick Mode (30 minutes)**: What runs, what's skipped
- **Deep Mode (6 hours)**: Full analysis workflow
- **Time allocations** for different operations
- **Parallel vs. sequential** task execution

**Requirements:**
- Show time efficiency gains from pre-processing
- Compare existing (6h) vs. new (30m) vs. unified (both) schedules
- Highlight cost optimization through scheduling

---

### Diagram 8: Before & After Comparison

Create **two side-by-side Mermaid flowcharts**:

**Left side - "Before" (Two Separate Systems):**
- Existing system flow (6h cron, PR monitoring)
- New system flow (30m reports, baseline tracking)
- Show them as disconnected
- Indicate duplicate infrastructure

**Right side - "After" (Unified System):**
- Single integrated flow
- Shared components
- Optimized scheduling
- Enhanced features from both

**Requirements:**
- Visual comparison showing consolidation
- Highlight eliminated duplication
- Show added integration points
- Indicate cost/efficiency improvements

---

## 🎨 Styling Guidelines

For all diagrams, use:
- **Consistent color scheme:**
  - `#e1f5fe` (light blue) - Data collection / inputs
  - `#e8f5e9` (light green) - Successful outputs
  - `#fff3e0` (light orange) - Processing / analysis
  - `#f3e5f5` (light purple) - Shared components
  - `#ffebee` (light red) - Critical paths / issues

- **Clear labels** with concise descriptions
- **Legend** when using color coding
- **Directional arrows** showing data flow
- **Grouped sections** for related components

---

## 📝 Output Format

For each diagram, provide:

1. **Diagram Title**
2. **Mermaid Code Block** (complete, ready to render)
3. **Description** (2-3 sentences explaining what it shows)
4. **Key Insights** (3-5 bullet points highlighting important aspects)

Example format:
```markdown
### Diagram 1: Existing System Architecture

[Mermaid code here]

**Description:** This diagram shows the current cron-based analysis system with sequential agent chaining orchestrated by CCR.

**Key Insights:**
- Runs every 6 hours on zo.computer
- Uses GLM 4.6 for primary analysis
- Sequential flow from data → analysis → visualization → output
- Cost optimized through model selection (<$0.50/day)
- Focuses on PR workflow pain points
```

---

## ✅ Success Criteria

Your diagrams should:
- [ ] Clearly show what exists vs. what's being added
- [ ] Illustrate how components integrate
- [ ] Provide multiple perspectives (conceptual, data flow, component)
- [ ] Use consistent styling and colors
- [ ] Be immediately understandable to developers
- [ ] Show both technical architecture and business value
- [ ] Highlight key differences and improvements in unified system

---

## 🚀 Begin Your Analysis

Review all the documentation files listed above, then create the 8 diagrams as specified. Focus on clarity, accuracy, and showing the evolution from separate systems to unified architecture.

**Start with Diagram 1 and work through all 8 systematically.**
