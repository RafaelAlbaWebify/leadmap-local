# Current project state

Updated: 2026-07-20

## Proven baseline

- Python 3.12 backend with FastAPI, SQLAlchemy 2, SQLite and Alembic.
- React 19 and TypeScript frontend built with Vite.
- Persistent territories, query templates, businesses, locations, search runs and observations.
- Ireland starter seed data with reusable business-query groups.
- Assisted discovery-plan preview without unattended browser automation.
- CSV and JSON lead exports.
- Local verification completed with Ruff, strict mypy, pytest, ESLint, Vitest and a production build.

## Current limits

- The live Playwright provider remains intentionally disabled.
- The map is still a placeholder; no GeoJSON ingestion or MapLibre layer exists yet.
- Candidate staging and approval are not implemented.
- No unattended crawl, CAPTCHA handling, proxy rotation or anti-detection behaviour is permitted.

## Immediate engineering order

1. Keep the published baseline green in GitHub Actions.
2. Add an Alembic migration smoke test on a clean temporary database.
3. Implement the geographic workspace as an independent vertical slice:
   - vetted Ireland boundary source,
   - import/validation pipeline,
   - stored geometry contract,
   - MapLibre rendering,
   - region selection,
   - fixture-based tests.
4. Only after geographic proof, implement the explicit assisted Playwright state machine.

## Definition of done for each change

- Change is made on a feature branch.
- Backend lint, formatting, strict typing and tests pass.
- Frontend lint, tests and production build pass when frontend code changes.
- Database changes include an Alembic migration and clean-database proof.
- The pull request records scope, proof, risk and rollback.
