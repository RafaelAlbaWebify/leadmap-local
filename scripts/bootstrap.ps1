param([switch]$SkipBrowserInstall)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory)][string]$Description,
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter()][string[]]$Arguments = @(),
        [Parameter()][string]$WorkingDirectory
    )

    Write-Host "==> $Description" -ForegroundColor Cyan
    $PreviousLocation = Get-Location
    try {
        if ($WorkingDirectory) { Set-Location $WorkingDirectory }
        & $FilePath @Arguments
        $ExitCode = $LASTEXITCODE
    }
    finally {
        if ($WorkingDirectory) { Set-Location $PreviousLocation }
    }

    if ($ExitCode -ne 0) {
        throw "$Description failed with exit code $ExitCode."
    }
}

if (-not (Test-Path $Python)) {
    throw "Virtual environment missing at $Python. Run the installation/recovery block first."
}

if (-not $NpmCommand) {
    throw "npm.cmd was not found on PATH."
}

Invoke-NativeChecked "Upgrading pip" $Python @("-m", "pip", "install", "--upgrade", "pip")
Invoke-NativeChecked "Installing backend dependencies" $Python @("-m", "pip", "install", "-e", ".[dev,browser]") $Root

if (-not $SkipBrowserInstall) {
    Invoke-NativeChecked "Installing Playwright Chromium" $Python @("-m", "playwright", "install", "chromium")
}

Invoke-NativeChecked "Installing frontend dependencies" $NpmCommand.Source @("install") (Join-Path $Root "frontend")

Write-Host ""
Write-Host "PASS: dependency bootstrap completed." -ForegroundColor Green
