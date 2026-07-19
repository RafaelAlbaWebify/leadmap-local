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

    Write-Host ""
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
    throw "Virtual environment missing at $Python."
}

if (-not $NpmCommand) {
    throw "npm.cmd was not found on PATH."
}

$PowerShellFiles = Get-ChildItem (Join-Path $Root "scripts") -Filter "*.ps1"
foreach ($File in $PowerShellFiles) {
    $Tokens = $null
    $Errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $File.FullName,
        [ref]$Tokens,
        [ref]$Errors
    ) | Out-Null

    if ($Errors.Count -gt 0) {
        throw "PowerShell syntax check failed for $($File.Name): $(
            ($Errors | ForEach-Object Message) -join '; '
        )"
    }
}

Invoke-NativeChecked "Backend lint" $Python @("-m", "ruff", "check", ".") $Root
Invoke-NativeChecked "Backend format check" $Python @("-m", "ruff", "format", "--check", ".") $Root
Invoke-NativeChecked "Python type checks" $Python @("-m", "mypy") $Root
Invoke-NativeChecked "Backend tests" $Python @("-m", "pytest") $Root
Invoke-NativeChecked "Frontend lint" $NpmCommand.Source @("run", "lint") (Join-Path $Root "frontend")
Invoke-NativeChecked "Frontend tests" $NpmCommand.Source @("run", "test") (Join-Path $Root "frontend")
Invoke-NativeChecked "Frontend build" $NpmCommand.Source @("run", "build") (Join-Path $Root "frontend")

Write-Host ""
Write-Host "PASS: all verification checks completed." -ForegroundColor Green
