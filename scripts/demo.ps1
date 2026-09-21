# One-command demo bring-up for Windows (PowerShell).
#   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
$ErrorActionPreference = "Stop"
docker compose up -d db redis
docker compose up -d --build api
docker compose exec -T api python scripts/init_db.py
docker compose exec -T api python scripts/seed_demo.py
$port = if ($env:API_HOST_PORT) { $env:API_HOST_PORT } else { "8000" }
Write-Host ""
Write-Host "  Demo ready -> http://localhost:$port/app"
Write-Host "  login: demo@openfrontdesk.local / demodemo12"
