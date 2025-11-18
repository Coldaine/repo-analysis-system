# Archived Prototype Files

**⚠️ DEPRECATED - DO NOT USE FOR NEW DEVELOPMENT**

**Archive Date**: November 17, 2025  
**Status**: Prototype implementation - superseded by new architecture  

## Files in This Directory

| File | Purpose | Status |
|------|---------|--------|
| `agentic_prototype.py` | Original prototype main script | DEPRECATED |
| `side_agent.py` | Original side agent implementations | DEPRECATED |
| `run_prototype.sh` | Original execution script | DEPRECATED |
| `langgraph_orchestrator.py` | Initial LangGraph implementation | DEPRECATED |

## Migration Information

All functionality from these files has been migrated to the new architecture:

- **New Main Entry Point**: `scripts/run_graph.py`
- **New Orchestration**: `src/orchestration/graph.py`
- **New Agent Implementations**: `src/agents/`
- **New Model Management**: `src/models/`

## Why This Was Archived

1. **Technical Debt**: The prototype accumulated significant technical debt
2. **Scaling Limitations**: Could not support multi-user concurrent access
3. **Architecture Constraints**: Monolithic structure limited extensibility
4. **LangGraph Integration**: Needed complete redesign for proper LangGraph adoption

## Reference Only

These files are preserved for:
- Understanding system evolution
- Reference for specific implementation details
- Historical context

**For current development, see the main project directory and new `src/` structure.**