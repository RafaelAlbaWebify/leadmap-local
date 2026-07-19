$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue

if (-not (Test-Path $Python)) {
    throw "Virtual environment missing at $Python."
}

if (-not $NpmCommand) {
    throw "npm.cmd was not found on PATH."
}

$BackendCommand = "Set-Location '$Root'; & '$Python' -m uvicorn backend.leadmap.main:app --reload --port 8000"
$FrontendRoot = Join-Path $Root "frontend"
$FrontendCommand = "Set-Location '$FrontendRoot'; & '$($NpmCommand.Source)' run dev"

Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $BackendCommand
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $FrontendCommand

Write-Host "PASS: backend and frontend development processes launched." -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
