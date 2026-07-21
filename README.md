# LeadMap Local

Local-first territory intelligence and lead research workbench.

## Status

The executable workspace now includes persistent territory and lead data, an attributed Ireland geographic-artifact pipeline, MapLibre boundary rendering, boundary-to-territory assignment, and coverage/freshness overlays. Automated Linux and Windows Playwright review verifies the real application shell with deterministic fixtures.

Live browser-source capture remains intentionally disabled until the assisted-session state machine is implemented and tested. CI and automated tests do not access Google Maps or download geographic data.

## Current vertical slices

1. Territory → query template → fixture capture → normalize/deduplicate → review table → freshness metadata → CSV/JSON export.
2. Downloaded Ireland GeoJSON → strict validation → provenance/checksum → atomic local artifact → MapLibre selection → territory linkage → coverage/freshness presentation.

## Technology

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, SQLite, Alembic
- Browser adapter: Playwright (headed, assisted-session design)
- Frontend: React, TypeScript, Vite, MapLibre
- Tests: pytest, Vitest, Linux and Windows Playwright
- Quality: Ruff, mypy, ESLint, TypeScript compiler
- Automation: GitHub Actions, Dependabot, pre-commit

## Quick start (Windows PowerShell)

```powershell
.\scripts\bootstrap.ps1
.\scripts\verify.ps1
.\scripts\run-dev.ps1
```

Backend: http://127.0.0.1:8000  
API docs: http://127.0.0.1:8000/docs  
Frontend: http://127.0.0.1:5173

## Set up the official Ireland boundaries

Run one command from the repository:

```powershell
.\scripts\setup-ireland-geography.ps1
```

This user-initiated setup command downloads the official Tailte Éireann 2026 local-authority GeoJSON, requires exactly 31 features, safely identifies the identifier and name fields, validates every geometry, records provenance and retrieval time, calculates a SHA-256 checksum, and writes a checksum-addressed artifact under `data/geography`. Repeating the command with unchanged source data is idempotent.

The application itself still performs no runtime geography download. Tests and CI remain network-free.

## Import another downloaded geographic source

Use the lower-level command when importing a different licensed GeoJSON or when explicit source-field overrides are required:

```powershell
.\scripts\import-geography.ps1 `
  -SourceFile "C:\Downloads\boundaries.geojson" `
  -IdField "<source identifier property>" `
  -NameField "<source name property>"
```

## Safety boundaries

- No unattended browser crawling.
- No CAPTCHA solving, proxy rotation, fingerprint spoofing or account automation.
- Browser sessions are user-initiated and visible by default.
- Live source adapters are isolated behind a provider interface.
- Tests and CI use fixtures and do not access Google Maps.
- Geographic data is imported only through an explicit user command; there is no application runtime fetch.
- Credentials and browser profiles are excluded from version control.
- Exports contain only explicitly selected business records.

See `docs/` for the product specification, architecture and delivery plan.
