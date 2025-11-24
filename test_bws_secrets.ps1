# Test script to verify Bitwarden Secrets Manager integration
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Bitwarden Secrets Manager Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check which secrets are available
$secretsFound = @()
$secretsExpected = @(
    "GITHUB_TOKEN",
    "GLM_API_KEY",
    "MINIMAX_API_KEY",
    "GITHUB_OWNER"
)

foreach ($secretName in $secretsExpected) {
    $value = [Environment]::GetEnvironmentVariable($secretName)
    if ($value) {
        $secretsFound += $secretName
        Write-Host "[OK] $secretName : Present (length: $($value.Length) chars)" -ForegroundColor Green
    } else {
        Write-Host "[MISS] $secretName : NOT FOUND" -ForegroundColor Yellow
    }
}

Write-Host "`nSummary: $($secretsFound.Count) of $($secretsExpected.Count) secrets injected" -ForegroundColor Cyan
