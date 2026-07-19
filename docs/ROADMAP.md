# Delivery roadmap

## Slice 0 — Baseline (included)

- Product and architecture documents
- Backend API health/dashboard contract
- Fixture discovery provider
- Deduplication and freshness logic
- React operational dashboard shell
- Backend/frontend tests
- CI, Dependabot and PowerShell automation

## Slice 1 — Persistence

- SQLAlchemy tables and repositories
- Alembic initial migration
- Territory, query-template, business, location and observation CRUD
- Seed Ireland query templates
- CSV and JSON export
- API contract tests

## Slice 2 — Geographic workspace

- Ireland county/local-authority GeoJSON import pipeline
- MapLibre map
- Region selection and custom GeoJSON territories
- Marker clustering
- Coverage/freshness layers

## Slice 3 — Assisted Playwright session

- Explicit session state machine
- Headed Chromium launcher
- Prepared query confirmation
- Capture-visible-results command
- Stop limits, cancellation and diagnostic bundle
- No unattended sequence

## Slice 4 — Candidate review

- Parser fixtures derived from approved sessions
- Candidate staging table
- Duplicate comparison
- Business/location linking
- Observation history and change detection

## Slice 5 — Integration

- Versioned export manifest
- GeoJSON, CSV and JSON packages
- WATCH handoff
- CRM import contract
- Export state and changed-since-export markers
