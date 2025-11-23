# Bitwarden Secrets Integration

**Status**: Canonical  
**Last Updated**: November 23, 2025

This quick-reference guide summarizes how the Repository Analysis System uses Bitwarden Secrets Manager for runtime injection. For the full configuration schema and troubleshooting steps, see [Config and Secrets](operations/Config-and-Secrets.md).

## 🔐 Required Setup

1. **Install the `bws` CLI**
   - Windows: download the latest release from [bitwarden/sdk](https://github.com/bitwarden/sdk/releases), unzip, and add `bws.exe` to your `PATH`.
   - Linux/macOS:
     ```bash
     curl -LO https://github.com/bitwarden/sdk/releases/latest/download/bws-x86_64-unknown-linux-gnu.zip
     unzip bws-*.zip && sudo mv bws /usr/local/bin/ && chmod +x /usr/local/bin/bws
     ```
2. **Create / obtain a machine account token** with read access to the secrets projects used by this repo.
3. **Store the token securely**
   - PowerShell: `$env:BWS_ACCESS_TOKEN = "<token>"` (persist via `$PROFILE` if desired).
   - Bash/Zsh: `export BWS_ACCESS_TOKEN="<token>"` in your shell profile.
4. **Verify access**
   ```bash
   bws secret list
   ```
5. **Run commands via Bitwarden**
   ```bash
   bws run -- python scripts/run_graph.py analyze --repos "owner/repo"
   ```

## 📦 Secrets Expected at Runtime

| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | GitHub API access for cloning and metadata. |
| `GITHUB_OWNER` | Default namespace when none is provided. |
| `GLM_API_KEY` | Access to GLM 4.6 for CCR routing. |
| `MINIMAX_API_KEY` | Access to MiniMax models. |
| `POSTGRES_CONNECTION_STRING` | LangGraph checkpointer + persistence backend. |
| `GOOGLE_SEARCH_KEY` / `GOOGLE_CX` *(optional)* | Enables deterministic search gathering. |

## 🧪 Local Validation

Use the helper scripts in the repo after configuring Bitwarden:

```powershell
# Confirm secrets have been provisioned
./check-secrets.ps1

# Run a lightweight injection smoke test
./test-bws-inject.ps1
```

If either script fails, revisit the detailed instructions in [Config and Secrets](operations/Config-and-Secrets.md) before attempting a full run.
