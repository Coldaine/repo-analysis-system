# Templates and Examples

**Status**: Canonical
**Last Updated**: November 23, 2025

## 📄 Agent Template

Use this template when creating a new agent.

```python
from langchain_core.messages import HumanMessage
from src.state import AgentState

def new_agent(state: AgentState):
    """
    [Description of what the agent does]
    """
    messages = state['messages']
    # ... logic ...
    return {"messages": ["Agent finished processing"]}
```

## 📝 Report Template

Standard format for analysis reports.

```markdown
# Analysis Report: {repo_name}
**Date**: {date}
**Run ID**: {run_id}

## Executive Summary
{summary}

## Key Findings
- **Architecture**: {architecture_notes}
- **Complexity**: {complexity_score}
- **Security**: {security_notes}

## Recommendations
1. {recommendation_1}
2. {recommendation_2}
```

## 🔧 Config Example

`config/new_config.yaml` example for a standard run.

```yaml
database:
  host: "db.example.com"
  name: "prod_db"

agents:
  forensics:
    model: "claude-3-5-sonnet"
    temperature: 0.2
```
