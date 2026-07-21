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

## Import downloaded geographic boundaries

The application never downloads boundary data at runtime. Download the licensed GeoJSON yourself, inspect its property names, and pass those property fields explicitly:

```powershell
.\scripts\import-geography.ps1 `
  -SourceFile "C:\Downloads\ireland-local-authorities.geojson" `
  -IdField "<source identifier property>" `
  -NameField "<source name property>"
```

The command validates the complete FeatureCollection, requires the expected 31 features by default, records provenance and retrieval time, calculates a SHA-256 checksum, and writes a checksum-addressed artifact under `data/geography`. Repeating an identical import is idempotent.

Use the optional parameters to override source metadata, artifact directory, expected feature count, or retrieval timestamp when importing a different licensed dataset.

## Safety boundaries

- No unattended browser crawling.
- No CAPTCHA solving, proxy rotation, fingerprint spoofing or account automation.
- Browser sessions are user-initiated and visible by default.
- Live source adapters are isolated behind a provider interface.
- Tests and CI use fixtures and do not access Google Maps.
- Geographic data is imported explicitly; there is no runtime network fetch.
- Credentials and browser profiles are excluded from version control.
- Exports contain only explicitly selected business records.

See `docs/` for the product specification, architecture and delivery plan.
