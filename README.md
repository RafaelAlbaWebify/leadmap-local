# LeadMap Local

Local-first territory intelligence and lead research workbench.

## Status

Architecture baseline and executable first vertical slice scaffold. The live Google Maps
adapter is intentionally not implemented yet. The repository runs entirely with fixture
data so the domain model, API, UI shell, exports, tests and CI can be verified before
binding the product to an unstable external interface.

## First vertical slice

Territory → query template → fixture capture → normalize/deduplicate → review table
→ freshness metadata → CSV/JSON export.

## Technology

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, SQLite, Alembic
- Browser adapter: Playwright (headed, assisted-session design)
- Frontend: React, TypeScript, Vite
- Tests: pytest, Vitest
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

## Safety boundaries

- No unattended browser crawling.
- No CAPTCHA solving, proxy rotation, fingerprint spoofing or account automation.
- Browser sessions are user-initiated and visible by default.
- Live source adapters are isolated behind a provider interface.
- Tests and CI use fixtures and do not access Google Maps.
- Credentials and browser profiles are excluded from version control.
- Exports contain only explicitly selected business records.

See `docs/` for the product specification, architecture and delivery plan.
