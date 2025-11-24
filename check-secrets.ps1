# Quick script to check current secrets status
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Current Secrets Status Check" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check BWS_ACCESS_TOKEN
if ($env:BWS_ACCESS_TOKEN) {
    Write-Host "[OK] BWS_ACCESS_TOKEN is set (length: $($env:BWS_ACCESS_TOKEN.Length) chars)" -ForegroundColor Green
} else {
    Write-Host "[MISS] BWS_ACCESS_TOKEN is NOT set" -ForegroundColor Red
}

Write-Host "`nRequired Secrets for repo-analysis-system:" -ForegroundColor Cyan
Write-Host "-------------------------------------------`n"

$requiredSecrets = @(
    @{Name="GITHUB_TOKEN"; Required=$true},
    @{Name="GITHUB_OWNER"; Required=$false},
    @{Name="GLM_API_KEY"; Required=$true},
    @{Name="MINIMAX_API_KEY"; Required=$false},
    @{Name="GOOGLE_SEARCH_KEY"; Required=$false},
    @{Name="GOOGLE_CX"; Required=$false}
)

$foundCount = 0
$missingRequired = @()

foreach ($secret in $requiredSecrets) {
    $value = [Environment]::GetEnvironmentVariable($secret.Name)
    $reqText = if ($secret.Required) { "(REQUIRED)" } else { "(optional)" }

    if ($value) {
        Write-Host "[OK] $($secret.Name) : Present (length: $($value.Length) chars) $reqText" -ForegroundColor Green
        $foundCount++
    } else {
        $color = if ($secret.Required) { "Red" } else { "Yellow" }
        Write-Host "[MISS] $($secret.Name) : NOT FOUND $reqText" -ForegroundColor $color
        if ($secret.Required) {
            $missingRequired += $secret.Name
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Summary: $foundCount of $($requiredSecrets.Count) secrets found" -ForegroundColor Cyan

if ($missingRequired.Count -gt 0) {
    Write-Host "`nMissing REQUIRED secrets:" -ForegroundColor Red
    foreach ($name in $missingRequired) {
        Write-Host "  - $name" -ForegroundColor Red
    }
}
