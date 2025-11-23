# Vision v2: Multi-Repo Parallel Agent Manager (Nov 17, 2025)

## Overview

This folder contains the enhanced vision for a comprehensive repository health tracking system with baseline management and parallel agent execution.

## Core Concepts

- **Repository Sync**: Auto-clone/remove based on GitHub account
- **Locked Baselines**: Immutable goals and phases per repository
- **Parallel Execution**: True parallel Claude instances via CCR
- **4 Pillars Framework**: Code Quality, Documentation, Testing, Goal Adherence
- **Pre-Processing**: Gather review items before AI analysis (60-70% faster)
- **Frequent Reporting**: Configurable status reports

## Technology Stack

- **Language**: Node.js
- **Orchestration**: CCR routing to Z.ai (98% cost savings)
- **Models**: Claude via CCR
- **Storage**: SQLite (baselines), JSON (state)
- **APIs**: GitHub, Git operations

## Innovations Over v1

1. **Baseline Management**: Non-modifiable goal anchors with divergence detection
2. **Parallel Agents**: Multiple Claude processes, not just sequential chaining
3. **Pre-Processing**: Review item gathering before AI analysis
4. **Goal Tracking**: 8 anchor goals with locked success criteria
5. **Higher Frequency**: Supports frequent reporting intervals

## Documents in this Vision

1. **Multi-Repo-Agent-Manager-Architecture.md** - Overall system architecture
2. **Pre-Processing-Script-Design.md** - Efficiency optimization layer
3. **Repository-Initialization-Template.md** - Baseline structure and format
4. **Status-Report-Template.md** - Periodic report format
5. **Implementation-Anchor-Goals.md** - 8 core goals and success criteria
6. **Architecture-Visualization-Prompt.md** - Guide for creating diagrams

## Status

📋 **Design Phase** - Comprehensive architecture documented
🔄 **Being Merged** - Integrating with Vision v1 for unified system
🎯 **Goal-Driven** - 8 locked anchor goals defined
