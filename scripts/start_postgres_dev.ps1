# Starts a local PostgreSQL 15 container for development using Docker
# Requires: Docker Desktop on Windows

param(
    [string]$DbPassword = "changeme",
    [string]$DbName = "repo_analysis",
    [int]$Port = 5432
)

Write-Host "Starting local PostgreSQL (port $Port, db '$DbName')..."

$env:DB_PASSWORD = $DbPassword
$env:DB_HOST = "localhost"
$env:DB_PORT = "$Port"
$env:DB_NAME = $DbName

# Use docker-compose if available for schema init; else fallback to docker run
if (Test-Path -Path "$(Join-Path $PSScriptRoot '..' 'docker-compose.yml')") {
    Push-Location (Join-Path $PSScriptRoot '..')
    try {
        docker compose up -d postgres
        Write-Host "PostgreSQL is starting. Run 'docker compose logs -f postgres' to follow logs." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    docker run --name repo-analysis-postgres -e POSTGRES_PASSWORD=$DbPassword -e POSTGRES_DB=$DbName -p ${Port}:5432 -v repo_analysis_pgdata:/var/lib/postgresql/data -d postgres:15-alpine
    Write-Host "PostgreSQL container 'repo-analysis-postgres' started." -ForegroundColor Green
}

Write-Host "Set these environment variables for the app:" -ForegroundColor Yellow
Write-Host "  DB_HOST=localhost" -ForegroundColor Yellow
Write-Host "  DB_PORT=$Port" -ForegroundColor Yellow
Write-Host "  DB_NAME=$DbName" -ForegroundColor Yellow
Write-Host "  DB_USER=postgres" -ForegroundColor Yellow
Write-Host "  DB_PASSWORD=$DbPassword" -ForegroundColor Yellow
