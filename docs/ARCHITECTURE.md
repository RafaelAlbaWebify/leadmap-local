# Architecture

## Context

The application is a local web workbench:

```text
React UI → FastAPI application → domain services → SQLite
                         ↘ discovery provider → fixture or headed Playwright
```

## Boundaries

### Domain

Owns territory, campaign, query, business, location, observation, review and export
concepts. It contains no browser selectors, React state or SQLAlchemy table logic.

### Discovery

Provider interface for user-approved acquisition. Fixture implementation is the default.
The Playwright adapter remains isolated and may be removed without invalidating stored
lead data.

### Persistence

SQLite initially. SQLAlchemy repositories and Alembic migrations enter when the first
persistent domain slice is implemented.

### UI

React and TypeScript. The visual shell follows the supplied operational-dashboard
references: fixed light sidebar, restrained cards, large map workspace and dense tables.

### Integration

Exports are versioned contracts. Other applications must not write directly to this
application's SQLite file.

## Reliability rules

- CI never accesses Google Maps.
- Parser behavior is proven against stored fixtures.
- Live sessions save bounded diagnostics on failure.
- Every database migration is reversible where SQLite permits.
- Export IDs are stable.
- Dates are stored as UTC and displayed in local time.
- External source observations are append-only; canonical records may be updated through
  explicit services.

## Planned slices

1. Architecture baseline and fixture-driven dashboard.
2. Persistent territories, query templates and leads.
3. MapLibre territory selection and GeoJSON.
4. Assisted Playwright session state machine.
5. Observation parser fixtures and candidate review.
6. Export packages and CRM contract.
7. Coverage matrix, freshness scheduling and change detection.
