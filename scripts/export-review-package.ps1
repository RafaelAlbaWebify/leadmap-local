$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Downloads = Join-Path $HOME "Downloads"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Zip = Join-Path $Downloads "LEADMAP_REVIEW_$Stamp.zip"

$Include = @(
    "README.md",
    "docs",
    "backend",
    "frontend/src",
    ".github",
    "pyproject.toml",
    "package.json"
)

Compress-Archive -Path ($Include | ForEach-Object { Join-Path $Root $_ }) -DestinationPath $Zip
Write-Host "PASS: $Zip" -ForegroundColor Green
