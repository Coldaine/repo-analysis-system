#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Migrate environment variables to Bitwarden Secrets Manager

.DESCRIPTION
    This script automates the migration of API keys and secrets from environment
    variables to Bitwarden Secrets Manager. It creates all required secrets in
    the specified Bitwarden project.

.PARAMETER ProjectName
    Name of the Bitwarden Secrets Manager project (default: "API Keys - Hot")

.PARAMETER DryRun
    Show what would be created without actually creating secrets

.EXAMPLE
    .\migrate-to-bitwarden.ps1

.EXAMPLE
    .\migrate-to-bitwarden.ps1 -ProjectName "Search & Research" -DryRun

.NOTES
    Prerequisites:
    - bws CLI installed and in PATH
    - BWS_ACCESS_TOKEN environment variable set
    - Bitwarden project already created
    - Machine account with write access to project
#>

param(
    [string]$ProjectName = "API Keys - Hot",
    [switch]$DryRun
)

# Color functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Banner
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Bitwarden Secrets Migration Tool" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check bws CLI
if (-not (Get-Command "bws" -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: bws CLI not found in PATH"
    Write-Host "Install from: https://github.com/bitwarden/sdk/releases"
    exit 1
}
Write-Success "✓ bws CLI found"

# Check access token
if (-not $env:BWS_ACCESS_TOKEN) {
    Write-Error "ERROR: BWS_ACCESS_TOKEN environment variable not set"
    Write-Host "`nSet it with:"
    Write-Host '  $env:BWS_ACCESS_TOKEN = "your_token_here"'
    exit 1
}
Write-Success "✓ BWS_ACCESS_TOKEN set"

# Verify token works
Write-Info "Verifying Bitwarden connection..."
try {
    $null = bws project list 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "bws command failed"
    }
} catch {
    Write-Error "ERROR: Cannot connect to Bitwarden"
    Write-Host "Check your BWS_ACCESS_TOKEN is valid"
    exit 1
}
Write-Success "✓ Connected to Bitwarden"

# Get project ID
Write-Info "Finding project '$ProjectName'..."
$projects = bws project list --output json | ConvertFrom-Json
$project = $projects | Where-Object { $_.name -eq $ProjectName }

if (-not $project) {
    Write-Error "ERROR: Project '$ProjectName' not found"
    Write-Host "`nAvailable projects:"
    $projects | ForEach-Object { Write-Host "  - $($_.name)" }
    Write-Host "`nCreate the project in Bitwarden web vault first, or specify existing project with -ProjectName"
    exit 1
}

$projectId = $project.id
Write-Success "✓ Found project: $ProjectName (ID: $projectId)"

# Check existing secrets
Write-Info "Checking existing secrets in project..."
$existingSecrets = bws secret list --output json | ConvertFrom-Json

# Define secrets to migrate
$secretsToMigrate = @(
    @{
        Name = "GITHUB_TOKEN"
        EnvVar = "GITHUB_TOKEN"
        Description = "GitHub API token for repository access"
        Required = $true
    },
    @{
        Name = "GITHUB_OWNER"
        EnvVar = "GITHUB_OWNER"
        Description = "Default repository owner"
        Required = $false
    },
    @{
        Name = "GLM_API_KEY"
        EnvVar = "GLM_API_KEY"
        Description = "GLM 4.6 API key for AI analysis"
        Required = $true
    },
    @{
        Name = "MINIMAX_API_KEY"
        EnvVar = "MINIMAX_API_KEY"
        Description = "MiniMax API key for lightweight AI tasks"
        Required = $false
    },
    @{
        Name = "GOOGLE_SEARCH_KEY"
        EnvVar = "GOOGLE_SEARCH_KEY"
        Description = "Google Custom Search API key"
        Required = $false
    },
    @{
        Name = "GOOGLE_CX"
        EnvVar = "GOOGLE_CX"
        Description = "Google Custom Search Engine ID"
        Required = $false
    }
)

Write-Host "`n----------------------------------------"
Write-Host "Migration Plan"
Write-Host "----------------------------------------`n"

$toCreate = @()
$toSkip = @()
$missing = @()

foreach ($secret in $secretsToMigrate) {
    $existingSecret = $existingSecrets | Where-Object { $_.key -eq $secret.Name }
    $envValue = [Environment]::GetEnvironmentVariable($secret.EnvVar)

    if ($existingSecret) {
        Write-Warning "SKIP: $($secret.Name) - Already exists in Bitwarden"
        $toSkip += $secret
    }
    elseif (-not $envValue) {
        if ($secret.Required) {
            Write-Error "MISSING: $($secret.Name) - Environment variable not set (REQUIRED)"
            $missing += $secret
        } else {
            Write-Warning "MISSING: $($secret.Name) - Environment variable not set (optional)"
            $missing += $secret
        }
    }
    else {
        $maskedValue = $envValue.Substring(0, [Math]::Min(10, $envValue.Length)) + "..."
        Write-Success "CREATE: $($secret.Name) - Found in environment ($maskedValue)"
        $toCreate += $secret
    }
}

# Summary
Write-Host "`n----------------------------------------"
Write-Host "Summary"
Write-Host "----------------------------------------"
Write-Host "To create: $($toCreate.Count)" -ForegroundColor Green
Write-Host "To skip: $($toSkip.Count)" -ForegroundColor Yellow
Write-Host "Missing: $($missing.Count)" -ForegroundColor $(if ($missing.Count -gt 0) { "Red" } else { "Gray" })

# Check for required missing secrets
$requiredMissing = $missing | Where-Object { $_.Required }
if ($requiredMissing.Count -gt 0) {
    Write-Host "`n----------------------------------------" -ForegroundColor Red
    Write-Error "ERROR: Required secrets are missing!"
    Write-Host "Set these environment variables before running migration:"
    foreach ($secret in $requiredMissing) {
        Write-Host "  - $($secret.EnvVar)"
    }
    exit 1
}

# Exit if nothing to do
if ($toCreate.Count -eq 0) {
    Write-Host "`n✓ All secrets already exist in Bitwarden - nothing to migrate" -ForegroundColor Green
    exit 0
}

# Dry run exit
if ($DryRun) {
    Write-Host "`n[DRY RUN] Would create $($toCreate.Count) secret(s)" -ForegroundColor Yellow
    Write-Host "Run without -DryRun to perform actual migration"
    exit 0
}

# Confirm migration
Write-Host "`n----------------------------------------"
Write-Host "Ready to migrate $($toCreate.Count) secret(s) to Bitwarden"
Write-Host "----------------------------------------"
$confirm = Read-Host "Continue? (yes/no)"

if ($confirm -ne "yes") {
    Write-Warning "Migration cancelled"
    exit 0
}

# Perform migration
Write-Host "`n----------------------------------------"
Write-Host "Migrating Secrets"
Write-Host "----------------------------------------`n"

$successCount = 0
$failureCount = 0

foreach ($secret in $toCreate) {
    $envValue = [Environment]::GetEnvironmentVariable($secret.EnvVar)

    Write-Info "Creating: $($secret.Name)..."

    try {
        $result = bws secret create $secret.Name $envValue $projectId --note $secret.Description 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Created: $($secret.Name)"
            $successCount++
        } else {
            throw "bws command failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error "✗ Failed: $($secret.Name) - $($_.Exception.Message)"
        $failureCount++
    }
}

# Final summary
Write-Host "`n========================================"
Write-Host "Migration Complete"
Write-Host "========================================`n"

Write-Success "Successfully created: $successCount secret(s)"
if ($failureCount -gt 0) {
    Write-Error "Failed: $failureCount secret(s)"
}

# Verify migration
Write-Info "`nVerifying migration..."
$allSecrets = bws secret list --output json | ConvertFrom-Json
$migratedSecrets = $allSecrets | Where-Object { $_.projectId -eq $projectId }

Write-Host "`nSecrets in project '$ProjectName':" -ForegroundColor Cyan
$migratedSecrets | Select-Object key, @{Name='Created'; Expression={$_.creationDate}} | Format-Table -AutoSize

# Next steps
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Next Steps" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "1. Test secret injection:"
Write-Host "   bws run -- python scripts/run_graph.py analyze --repos \"owner/repo\"`n"

Write-Host "2. Verify secrets are loaded:"
Write-Host "   bws run -- env | grep -E 'GITHUB_TOKEN|GLM_API_KEY'`n"

Write-Host "3. Update your shell profile to remove old environment variables"
Write-Host "   (Keep BWS_ACCESS_TOKEN only)`n"

Write-Host "4. For GitHub Actions setup, see:"
Write-Host "   docs/Bitwarden-Secrets-Integration.md`n"

Write-Success "Migration completed successfully!"
