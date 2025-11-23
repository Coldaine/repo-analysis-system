# Test Bitwarden secrets injection
Write-Host "`nTesting Bitwarden Secrets Injection" -ForegroundColor Cyan
Write-Host "===================================`n" -ForegroundColor Cyan

Write-Host "Running command with bws run wrapper..." -ForegroundColor Yellow
Write-Host "Command: bws run -- powershell -ExecutionPolicy Bypass -File check-secrets.ps1`n" -ForegroundColor Gray

bws run -- powershell -ExecutionPolicy Bypass -File check-secrets.ps1
