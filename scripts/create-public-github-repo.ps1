param([string]$RepositoryName = "leadmap-local")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
$Git = Get-Command git.exe -ErrorAction SilentlyContinue
$Gh = Get-Command gh.exe -ErrorAction SilentlyContinue

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory)][string]$Description,
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter()][string[]]$Arguments = @()
    )

    Write-Host "==> $Description" -ForegroundColor Cyan
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

if (-not $Git) { throw "git.exe was not found on PATH." }
if (-not $Gh) { throw "gh.exe was not found on PATH. Install GitHub CLI and run 'gh auth login'." }

Set-Location $Root

if (-not (Test-Path ".git")) {
    Invoke-NativeChecked "Initialising Git" $Git.Source @("init")
    Invoke-NativeChecked "Selecting main branch" $Git.Source @("branch", "-M", "main")
}

Invoke-NativeChecked "Staging files" $Git.Source @("add", ".")

& $Git.Source diff --cached --quiet
$HasNoStagedChanges = ($LASTEXITCODE -eq 0)
if (-not $HasNoStagedChanges) {
    Invoke-NativeChecked "Creating baseline commit" $Git.Source @(
        "commit",
        "-m",
        "chore: establish LeadMap architecture baseline"
    )
}

& $Git.Source remote get-url origin *> $null
$HasOrigin = ($LASTEXITCODE -eq 0)

if ($HasOrigin) {
    Invoke-NativeChecked "Pushing repository" $Git.Source @("push", "-u", "origin", "main")
}
else {
    Invoke-NativeChecked "Creating public GitHub repository" $Gh.Source @(
        "repo", "create", $RepositoryName,
        "--public", "--source", ".", "--remote", "origin", "--push"
    )
}

Write-Host "PASS: repository is committed and pushed." -ForegroundColor Green
