# Bitwarden Secrets Manager - Quick Start Guide

Quick reference for using Bitwarden Secrets Manager with this repository.

## First-Time Setup

### 1. Install bws CLI

**Windows**:
```powershell
# Download from https://github.com/bitwarden/sdk/releases
# Extract bws.exe and add to PATH
```

**Linux/macOS**:
```bash
curl -LO https://github.com/bitwarden/sdk/releases/latest/download/bws-x86_64-unknown-linux-gnu.zip
unzip bws-*.zip
sudo mv bws /usr/local/bin/
chmod +x /usr/local/bin/bws
```

### 2. Get Your Access Token

1. Go to https://vault.bitwarden.com
2. Navigate to **Secrets Manager** → **Machine Accounts**
3. Find or create machine account for this repository
4. Generate access token (save it securely!)

### 3. Configure Token

**Windows (PowerShell)**:
```powershell
# Store securely
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.bws"
Set-Content -Path "$env:USERPROFILE\.bws\repo-analysis-token.txt" -Value "YOUR_TOKEN_HERE"
(Get-Item "$env:USERPROFILE\.bws\repo-analysis-token.txt").Attributes += 'Hidden'

# Add to PowerShell profile for auto-load
Add-Content -Path $PROFILE -Value "`n`$env:BWS_ACCESS_TOKEN = Get-Content -Path `"`$env:USERPROFILE\.bws\repo-analysis-token.txt`" -ErrorAction SilentlyContinue"
```

**Linux/macOS**:
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export BWS_ACCESS_TOKEN="YOUR_TOKEN_HERE"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Verify Setup

```bash
# List all secrets (should show 6 secrets)
bws secret list

# Expected secrets:
# - GITHUB_TOKEN
# - GITHUB_OWNER
# - GLM_API_KEY
# - MINIMAX_API_KEY
# - GOOGLE_SEARCH_KEY
# - GOOGLE_CX
```

---

## Daily Usage

### Run Prototype Locally

```bash
# Secrets automatically injected at runtime
bws run -- python agentic_prototype.py

# Or use the wrapper script
bws run -- ./run_prototype.sh
```

### Run with Verbose Output

```bash
bws run -- python agentic_prototype.py --verbose
```

### Check Which Secrets Are Loaded

```bash
# List available secrets
bws secret list

# Get specific secret details (without value)
bws secret get <secret-id>

# Get secret value (use carefully - visible in terminal!)
bws secret get <secret-id> | jq -r '.value'
```

---

## Common Commands

### List Secrets

```bash
# All secrets
bws secret list

# Pretty table format (PowerShell)
bws secret list --output json | ConvertFrom-Json | Select-Object id, key | Format-Table

# Search for specific secret
bws secret list --output json | ConvertFrom-Json | Where-Object { $_.key -like "*GITHUB*" }
```

### Update a Secret

```bash
# Get secret ID first
bws secret list

# Update secret value
bws secret edit <secret-id> --value "new_secret_value"

# All systems automatically get new value on next run!
```

### Add New Secret

```bash
# Get project ID
bws project list

# Create new secret
bws secret create "SECRET_NAME" "secret_value" <project-id> --note "Description"
```

### Test Secret Injection

```bash
# Verify secrets are injected into environment
bws run -- env | grep -E "GITHUB_TOKEN|GLM_API_KEY|MINIMAX_API_KEY"
```

---

## Troubleshooting

### "bws: command not found"

**Problem**: bws CLI not installed or not in PATH

**Solution**:
```bash
# Windows: Add directory containing bws.exe to PATH
# Linux/macOS: Ensure bws is in /usr/local/bin/
which bws  # Should show path to bws
```

### "Unauthorized" Error

**Problem**: Invalid or missing access token

**Solution**:
```bash
# Check token is set
echo $BWS_ACCESS_TOKEN  # Linux/macOS
echo $env:BWS_ACCESS_TOKEN  # Windows PowerShell

# If empty, reload from file or re-export
source ~/.bashrc  # Linux/macOS
. $PROFILE  # Windows PowerShell
```

### Secrets Not Injecting

**Problem**: Environment variables not appearing in Python

**Solution**:
```bash
# Verify bws run is actually working
bws run -- env | grep GITHUB_TOKEN

# If empty, check:
# 1. BWS_ACCESS_TOKEN is set
# 2. Machine account has access to project
# 3. Secrets exist in project
bws secret list  # Should show your secrets
```

### Rate Limiting

**Problem**: Too many API calls to Bitwarden

**Solution**:
- Cache secrets locally during development
- Use `bws run` which fetches once per execution
- Avoid calling `bws secret get` repeatedly in loops

---

## GitHub Actions Integration

### Setup

1. Add `BWS_ACCESS_TOKEN` to GitHub repository secrets:
   - Settings → Secrets and variables → Actions
   - New repository secret: `BWS_ACCESS_TOKEN`

2. Get secret IDs for workflow:
```powershell
bws secret list --output json | ConvertFrom-Json | Select-Object id, key
```

3. Update `.github/workflows/analyze.yml` with actual secret IDs

4. Test workflow manually via Actions tab

---

## Security Best Practices

1. **Never commit** `.env` files or `BWS_ACCESS_TOKEN`
2. **Store tokens securely** in OS keychain or hidden files
3. **Rotate tokens** every 90 days
4. **Use separate tokens** for local vs CI/CD if possible
5. **Check audit logs** regularly in Bitwarden web vault
6. **Revoke immediately** if token is compromised

---

## Full Documentation

For complete setup instructions, architecture details, and advanced usage:

**See**: [docs/Bitwarden-Secrets-Integration.md](docs/Bitwarden-Secrets-Integration.md)

---

## Quick Reference: Essential Commands

```bash
# Daily use
bws run -- python agentic_prototype.py

# List secrets
bws secret list

# Update secret
bws secret edit <id> --value "new_value"

# Verify setup
bws secret list && echo "✅ Bitwarden configured correctly"
```

---

**Need Help?** See the full integration guide: `docs/Bitwarden-Secrets-Integration.md`
