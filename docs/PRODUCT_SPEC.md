# Product specification

## Purpose

LeadMap Local helps one operator plan territory-based business discovery, capture
user-approved search results, maintain dated observations, review lead suitability,
and export stable records to CRM and website-analysis tools.

## Initial market

Republic of Ireland. The geographic model must later support the UK, USA, Canada,
Australia and New Zealand without renaming core concepts.

## Core users

A single business operator performing controlled lead research.

## Core workflow

1. Select or create a territory.
2. Select a reusable country-aware query template.
3. Start an assisted visible browser session.
4. Review the prepared query.
5. Capture a bounded result set.
6. Normalize and deduplicate observations.
7. Review candidates.
8. Export selected, qualified records with stable IDs and timestamps.
9. Revisit stale territories and observations.

## Must-have capabilities

- Territory hierarchy and custom geographic areas.
- Query library grouped by sector.
- Explicit acquisition timestamps and observation history.
- Business versus business-location separation.
- Lead review and qualification states.
- Duplicate review rather than destructive silent merging.
- Map, coverage matrix and database views.
- CSV/JSON/GeoJSON export with schema version.
- Provider-independent acquisition boundary.
- Diagnostic evidence when the browser adapter fails.

## Non-goals for first release

- Unattended crawling.
- Automated outreach.
- CAPTCHA bypass or anti-detection mechanisms.
- Review-text collection.
- Multi-user cloud hosting.
- Bidirectional CRM synchronization.
- Claims of complete market coverage.

## First vertical slice acceptance

- Fixture capture works without network access.
- Duplicate provider identities collapse within one capture.
- Timestamps and freshness remain visible through API and UI.
- Dashboard shell renders from the backend contract.
- CI checks backend and frontend independently.
- Live browser capture remains disabled until parser evidence exists.
