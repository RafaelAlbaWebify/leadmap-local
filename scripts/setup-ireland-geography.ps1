param(
    [string]$ArtifactDirectory = "data/geography"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $projectPython)) {
    throw "Project Python not found at $projectPython. Run scripts\bootstrap.ps1 first."
}

Push-Location $repoRoot
try {
    Write-Host "Downloading and grouping the official Tailte Éireann 2026 local-authority boundaries..."
    & $projectPython -m backend.leadmap.geography.official_setup `
        --artifact-directory $ArtifactDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Official Ireland geography setup failed with exit code $LASTEXITCODE."
    }
    Write-Host "Official Ireland geography setup completed."
}
finally {
    Pop-Location
}
