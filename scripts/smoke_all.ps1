# Run API smoke tests against real Cosmos, then Cypress e2e against localhost:3000.
# Requires docker compose to be up (docker compose up -d) before running.
#
# Usage:
#   .\scripts\smoke_all.ps1
#
# Exit code: 0 = all passed, 1 = API smoke failed, 2 = Cypress failed

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

# Load .env.local into this process
$envFile = Join-Path $root ".env.local"
if (-not (Test-Path $envFile)) {
    Write-Error ".env.local not found — copy .env.local.example and fill in credentials"
    exit 1
}
foreach ($line in Get-Content $envFile) {
    if ($line -match "^\s*#" -or $line -notmatch "=") { continue }
    $parts = $line -split "=", 2
    [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
}

# --- Step 1: API smoke tests ---
Write-Host "`n=== API smoke tests ===" -ForegroundColor Cyan
Push-Location $root
uv run tox -e smoke
$apiExit = $LASTEXITCODE
Pop-Location

if ($apiExit -ne 0) {
    Write-Host "`nAPI smoke tests FAILED (exit $apiExit)" -ForegroundColor Red
    exit 1
}
Write-Host "API smoke tests passed" -ForegroundColor Green

# --- Step 2: Cypress e2e against the running web container ---
Write-Host "`n=== Cypress e2e ===" -ForegroundColor Cyan

# Verify web is up
try {
    $null = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
} catch {
    Write-Error "localhost:3000 is not reachable — is 'docker compose up' running?"
    exit 1
}

Push-Location (Join-Path $root "web")
$env:ELECTRON_RUN_AS_NODE = ""
pnpm e2e
$cypressExit = $LASTEXITCODE
Pop-Location

if ($cypressExit -ne 0) {
    Write-Host "`nCypress e2e FAILED (exit $cypressExit)" -ForegroundColor Red
    exit 2
}
Write-Host "`nAll smoke checks passed" -ForegroundColor Green
exit 0
