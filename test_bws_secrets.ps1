# Test script to verify Bitwarden Secrets Manager integration
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Bitwarden Secrets Manager Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check which secrets are available
$secretsFound = @()
$secretsExpected = @(
    "Z_AI_API_KEY",
    "OPENAI_API_KEY_1",
    "GROQ_API_KEY",
    "PERPLEXITY_API_KEY",
    "EXA_API_KEY",
    "GITHUB_TOKEN"
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
