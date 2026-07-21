param(
    [string]$ArtifactDirectory = "data/geography"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    Write-Host "Downloading and validating the official Tailte Éireann 2026 local-authority boundaries..."
    & python -m backend.leadmap.geography.official_setup `
        --artifact-directory $ArtifactDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Official Ireland geography setup failed with exit code $LASTEXITCODE."
    }
    Write-Host "Official Ireland geography setup completed."
}
finally {
    Pop-Location
}
