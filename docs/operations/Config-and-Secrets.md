# Configuration and Secrets

**Status**: Canonical
**Last Updated**: November 23, 2025

## 🔐 Secrets Management (Bitwarden)

We use **Bitwarden Secrets Manager** for all secret handling. **No secrets are stored in `.env` files.**

### Setup Guide (Quickstart)
1. **Install `bws` CLI**
   - Windows: Download from [Bitwarden SDK Releases](https://github.com/bitwarden/sdk/releases), extract `bws.exe`, and add to PATH.
   - Linux/macOS:
     ```bash
     curl -LO https://github.com/bitwarden/sdk/releases/latest/download/bws-x86_64-unknown-linux-gnu.zip
     unzip bws-*.zip && sudo mv bws /usr/local/bin/ && chmod +x /usr/local/bin/bws
     ```
2. **Machine Account & Token**
   - Create a Bitwarden Secrets Manager Machine Account with read access to this project.
   - Set `BWS_ACCESS_TOKEN`:
     - PowerShell: save token to `%USERPROFILE%\.bws\repo-analysis-token.txt`, optionally load in `$PROFILE`; or `$env:BWS_ACCESS_TOKEN="YOUR_TOKEN"`.
     - Bash: `export BWS_ACCESS_TOKEN="YOUR_TOKEN"` in shell profile.
3. **Verify**: `bws secret list` should show expected secrets.
4. **Run with Injection**:
   ```bash
   bws run -- python scripts/run_graph.py analyze
   ```

### Required Secrets
| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | API access for cloning and fetching data. |
| `GITHUB_OWNER` | Default repository owner/namespace. |
| `GLM_API_KEY` | Access to GLM models (CCR routing). |
| `MINIMAX_API_KEY` | Access to MiniMax models. |
| `POSTGRES_PASSWORD` | Database access. |
| `GOOGLE_SEARCH_KEY` | Search integration (optional). |
| `GOOGLE_CX` | Google Custom Search Engine ID (optional). |

---

## ⚙️ Configuration (`config/new_config.yaml`)

The system uses a YAML configuration file for non-sensitive settings.

### Core Structure

```yaml
version: "2.0"

# Database (PostgreSQL)
database:
  host: "localhost"
  port: 5432
  name: "repo_analysis"
  user: "postgres"
  pool_size: 10

# Orchestration
orchestration:
  langgraph:
    max_concurrent_runs: 5
    timeout_seconds: 3600
    retry_attempts: 3
  scheduling:
    default_type: webhook
    dormancy_audit_minutes: 30

# Model Providers
models:
  glm_4_6:
    base_url: "https://open.bigmodel.cn/api/paas/v4/"
    model: "glm-4.6"
  minimax:
    base_url: "https://api.minimax.chat/v1/"
    model: "abab6.5s-chat"
  ollama:
    base_url: "http://localhost:11434/v1/"

# Agent Configuration
agents:
  forensics:
    model: "claude-3-5-sonnet"
  complexity:
    enabled: true
  pr_review:
    enabled: false
    enable_github_commenting: false
    max_prs_per_repo: 10
```

## 🔄 Migration Guide

### From `config.yaml` to `new_config.yaml`
1.  Backup `config.yaml`.
2.  Run `python scripts/run_graph.py migrate --legacy-config config.yaml`.
3.  Verify `config/new_config.yaml` is created.

### From `.env` to Bitwarden
1.  Identify all secrets in `.env`.
2.  Add them to the Bitwarden project (scoped machine account).
3.  Delete `.env` locally and in CI.
4.  Update launch scripts to use `bws run` (local/systemd) or `bitwarden/sm-action@v1` (GitHub Actions).
5.  For cron/systemd: wrap service/timer with `BWS_ACCESS_TOKEN` and `bws run -- python scripts/run_graph.py ...`.
