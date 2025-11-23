# Blueprint Alignment & Decisions Architecture

## Overview
This document outlines the architecture for the **Blueprint Alignment System**, a subsystem designed to validate that the repository's implementation matches its documented architectural intent. 

Unlike traditional linters that check syntax, this system checks **meaning**. It uses LLMs to read documentation, synthesize a "Mental Model" (Blueprint) of the system, and then audit the codebase to ensure it adheres to that plan.

## Core Philosophy: LLM-First Reasoning
We do not use regex or rigid parsing to find "keywords". We use LLMs to **understand** intent.
- **Don't** grep for "PostgreSQL".
- **Do** ask the LLM: "Based on the history and config, what is the intended storage layer?"

## The Pipeline

### 1. Documentation Catalog Agent (The Archivist)
**Goal:** Discover every source of "Intent" in the repo.
**Mechanism:**
- Feeds file tree and file contents to LLM.
- **Prompt:** "Identify all files that describe how this system *should* work. Look for READMEs, architecture docs, config files, and high-level code comments."
- **Output:** A structured list of "Intent Sources" ranked by apparent authority.

### 2. Pillar Extraction Agent (The Architect)
**Goal:** Synthesize a coherent "Blueprint" from the fragmented intent sources.
**Mechanism:**
- Feeds the content of "Intent Sources" to LLM.
- **Prompt:** "Ignore the code. Read these documents and tell me the 3-5 core 'Architectural Pillars' of this system. What are the non-negotiable design decisions?"
- **Output:** `architectural_pillars.md` (e.g., "Pillar 1: Event-Driven Architecture", "Pillar 2: PostgreSQL Storage").

### 3. Implementation Validator Agent (The Auditor)
**Goal:** Compare the Blueprint against Reality.
**Mechanism:**
- Feeds the "Pillars" and the Source Code to LLM.
- **Prompt:** "Here is the Blueprint. Here is the Code. For each pillar, does the code implement it? Is it partial? Is it completely missing? Cite your evidence."
- **Output:** `implementation_state.md` (Gap Analysis).

---

## The Decisions Agent (Forensics & Conflict Resolution)

**Trigger:** Activates when the **Pillar Extraction Agent** finds conflicting information (e.g., "README says SQLite, but `docker-compose` says Postgres").

**Goal:** Determine the "True Intent" using forensic history, not just current file state.

### The "Golden Rule" of Truth
1.  **`/docs/` > `README.md`**: Detailed docs usually outweigh the README (which rots).
2.  **Pivot > History**: A recent "Refactor" or "Pivot" commit overrides *all* older documentation.
3.  **Code > Comments**: Working code is the ultimate reality, but if it contradicts docs, it might be "Drift" rather than "Intent".

### Logic Flow (LLM-Driven)
1.  **Gather Evidence:**
    - The agent pulls `git log` and `git blame` for the conflicting files.
    - It does **not** regex for keywords.
    - It feeds the raw commit history (messages, dates, authors) into the LLM.
2.  **The Prompt:**
    > "You are a Software Historian.
    > Document A (updated 2023) says X.
    > Document B (updated 2025) says Y.
    > The Git History shows a 'Major Refactor' commit in 2024.
    > What is the True Intent of this project right now?"
3.  **The Verdict:**
    - The LLM decides which source is authoritative.
    - It updates the Blueprint to reflect the "True Intent".
    - It flags the "Rotting" document for deletion/update.

## Integration Plan
- **Orchestrator:** LangGraph nodes for each agent.
- **State:** `AgentState` carries the `blueprint`, `conflicts`, and `verdict`.
- **Routing:**
    - `DocCatalog` -> `PillarExtraction`
    - If `PillarExtraction` detects conflict -> `DecisionsAgent`
    - Else -> `ImplementationValidator`

## Agent Tooling Manifest (The "Agency" Layer)

To enable true autonomy, agents are not just prompts—they are **Tool Users**. Each agent is equipped with a specific "Toolbox" of Python functions they can invoke to explore, verify, and reason.

### 1. The Archivist (DocCatalog Agent)
**Role:** Explorer & Librarian
**Capabilities:** Read-only file system traversal.
**Toolbox:**
- `list_directory(path)`: To discover file structure.
- `read_file(path)`: To read content of READMEs, docs, and configs.
- `find_files(pattern)`: To locate specific file types (e.g., `*.md`, `Dockerfile`).

### 2. The Architect (PillarExtraction Agent)
**Role:** Synthesizer & Planner
**Capabilities:** Deep reading and cross-referencing.
**Toolbox:**
- `read_file(path)`: To read full text of architectural docs.
- `consult_expert_model(query, context)`: **Critical.** Allows the agent to offload complex reasoning to a stronger model (e.g., "Analyze this 500-line config and extract the implicit architecture").

### 3. The Auditor (ImplementationValidator Agent)
**Role:** Investigator & Verifier
**Capabilities:** Codebase searching and pattern matching.
**Toolbox:**
- `grep_search(pattern)`: To find specific imports, class names, or comments.
- `file_search(glob)`: To verify existence of expected files (e.g., "Is there a `migrations/` folder?").
- `read_file(path)`: To inspect implementation details.
- `check_import(module_name)`: To verify if a library is actually used.

### 4. The Decisions Agent (Forensics & Conflict Resolution)
**Role:** **High-Agency Investigator** (The "Detective")
**Capabilities:** Multi-step inquiry, historical analysis, and deep reasoning.
**Behavior:** This agent does not just run one command. It forms hypotheses, gathers evidence, and iterates.
**Toolbox:**
- `git_log(file_path, limit)`: To see *when* a file changed.
- `git_blame(file_path)`: To see *who* changed specific lines.
- `git_diff(commit_a, commit_b)`: To see *what* exactly changed in a pivot.
- `git_show(commit_hash)`: To read the full context of a "Pivot Commit".
- `read_file(path)`: To compare current state vs. historical state.
- `consult_expert_model(query, complex_context)`: To ask a "Smarter Brain" to interpret a messy diff or ambiguous commit message.
    - *Example:* "I see a massive diff in commit `a1b2c`. Was this a refactor from Monolith to Microservices, or just a code cleanup? Here is the diff..."

**Example "Decisions" Workflow (Multi-Step):**
1.  **Thought:** "The README says 'No Database', but `requirements.txt` has `psycopg2`. I suspect a pivot."
2.  **Action:** `git_log("requirements.txt")` -> Finds commit `xyz`: "Add Postgres".
3.  **Thought:** "Okay, when was that? 2 weeks ago. When was README updated?"
4.  **Action:** `git_log("README.md")` -> Finds last update 2 years ago.
5.  **Thought:** "The README is rotting. But wait, is `psycopg2` actually used?"
6.  **Action:** `grep_search("import psycopg2")` -> Finds usage in `src/db.py`.
7.  **Verdict:** "The README is incorrect. The project uses PostgreSQL."
