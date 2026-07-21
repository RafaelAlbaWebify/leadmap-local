param(
    [Parameter(Mandatory = $true)]
    [string]$SourceFile,

    [Parameter(Mandatory = $true)]
    [string]$IdField,

    [Parameter(Mandatory = $true)]
    [string]$NameField,

    [string]$ArtifactDirectory = "data/geography",
    [string]$DatasetTitle = "Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
    [string]$Publisher = "Tailte Éireann",
    [string]$Licence = "CC BY 4.0",
    [int]$EditionYear = 2026,
    [string]$SourceUrl = "https://data-osi.opendata.arcgis.com/",
    [string]$RetrievedAt = (Get-Date).ToUniversalTime().ToString("o"),
    [int]$ExpectedFeatureCount = 31
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $arguments = @(
        "-m", "backend.leadmap.geography.cli",
        $SourceFile,
        "--artifact-directory", $ArtifactDirectory,
        "--dataset-title", $DatasetTitle,
        "--publisher", $Publisher,
        "--licence", $Licence,
        "--edition-year", $EditionYear,
        "--source-url", $SourceUrl,
        "--retrieved-at", $RetrievedAt,
        "--id-field", $IdField,
        "--name-field", $NameField,
        "--expected-feature-count", $ExpectedFeatureCount
    )
    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Geography import failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
