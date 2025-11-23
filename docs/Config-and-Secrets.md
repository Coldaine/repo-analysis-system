# Configuration and Secrets

**Status**: Canonical
**Last Updated**: November 23, 2025

## 🔐 Secrets Management (Bitwarden)

- We use **Bitwarden Secrets Manager** for all secret handling. **No secrets are stored in `.env` files.**
- Local/Systemd: `bws run -- python scripts/run_graph.py ...`
- GitHub Actions: `bitwarden/sm-action@v1` (injects secrets at runtime; nothing written to disk).
- Machine accounts: scoped read access to Bitwarden projects; GitHub tokens scoped minimally.

### Required Secrets
| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | API access for cloning and fetching data. |
| `GITHUB_OWNER` | Default repository owner/namespace. |
| `GLM_API_KEY` | Access to GLM models (CCR routing). |
| `MINIMAX_API_KEY` | Access to MiniMax models. |
| `POSTGRES_PASSWORD` | Database access. |
| `GOOGLE_SEARCH_KEY` / `GOOGLE_CX` | Search integration. |

## ⚙️ Configuration (`config/new_config.yaml`)

The system uses a YAML configuration file for non-sensitive settings.

```yaml
database:
  host: "localhost"
  port: 5432
  name: "repo_analysis"
  user: "postgres"

orchestration:
  langgraph:
    max_concurrent_runs: 5
    recursion_limit: 25
    checkpointer: "postgres"
  scheduling:
    default_type: webhook
    dormant_audit_minutes: 30

agents:
  forensics:
    model: "claude-3-5-sonnet"
  complexity:
    enabled: true
  pr_review:
    enabled: false
    enable_github_commenting: false
```

## 🔄 Migration Guide

### From `config.yaml` to `new_config.yaml`
1.  Backup `config.yaml`.
2.  Run `python scripts/run_graph.py migrate --legacy-config config.yaml`.
3.  Verify `config/new_config.yaml` is created.

### From `.env` to Bitwarden
1.  Identify all secrets in `.env`.
2.  Add them to the Bitwarden project.
3.  Delete `.env`.
4.  Update launch scripts to use `bws run`.
