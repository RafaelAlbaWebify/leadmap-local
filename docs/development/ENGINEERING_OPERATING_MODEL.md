# Engineering operating model

This document adapts the project operating prompt into repository policy. `AGENTS.md` contains the concise mandatory rules; `CONTRIBUTING.md` contains contributor workflow; the PR and scope-ledger templates make the rules operational.

## Product purpose worth preserving

LeadMap is a local-first territory intelligence and assisted lead-research workbench. It should help an operator define territories and query templates, review observations, retain provenance and export useful lead data without unattended scraping or opaque automation.

## Valuable current workflows

- Persistent territories, query templates, businesses, locations, search runs and observations.
- Explicit discovery-plan preview.
- CSV and JSON exports.
- Strict, network-free GeoJSON validation and import provenance.
- Repository-native branch, PR and exact-head CI workflow.

## Reusable architecture

- FastAPI API boundary.
- Domain models separated from SQLAlchemy persistence.
- Service modules for normalization, seeding, export and geography.
- Alembic-managed schema.
- React/TypeScript frontend separated from backend concerns.
- Deterministic fixtures and isolated tests.

## Technical debt and constraints

- The geographic workspace is not yet connected to a read-only API or MapLibre UI.
- Live Playwright collection remains intentionally disabled.
- Real Windows/browser acceptance is not yet proof for geographic UI work.
- Release and public presentation are separate future gates.

## Current proof

GitHub Actions is required to prove Ruff, formatting, strict mypy, backend tests, frontend lint, frontend tests and production build for the exact PR head. Additional manual or real-environment gates must be recorded when relevant.

## Documentation claim rule

Documentation must describe verified current behavior. Planned work belongs in roadmap or issues and must not be written as implemented.

## Current path

Continue the current implementation in small vertical slices. Refactor only where evidence identifies a specific design defect. No full rewrite is justified by the verified architecture or tests.