# ADR 0001: Ireland local-authority boundaries as the primary territory layer

- Status: Accepted
- Date: 2026-07-20
- Issue: #6

## Context

LeadMap needs an authoritative geographic layer for operational territory planning in Ireland. The first geographic slice must remain local-first, deterministic and testable without network access during normal application startup or CI.

Two suitable Tailte Éireann datasets are available through Ireland's open-data portal:

1. Local Authorities - National Statutory Boundaries - Ungeneralised 2026.
2. Counties - National Statutory Boundaries - Ungeneralised 2026.

The product's immediate need is to plan searches and measure coverage across practical administrative areas rather than reproduce traditional county geography.

## Decision

Use **Local Authorities - National Statutory Boundaries - Ungeneralised 2026** as the primary operational boundary layer.

Primary GeoJSON resource:

`https://data-osi.opendata.arcgis.com/api/download/v1/items/74b839e09e1c48f2b2fe4efccb52a73d/geojson?layers=3`

Publisher: Tailte Éireann.

Licence: Creative Commons Attribution 4.0.

Expected edition: 2026.

Expected operational coverage: 31 local-authority areas.

The statutory counties dataset may be added later as an optional reference layer, but it is not the primary territory contract.

## Import boundary

The application must not fetch the upstream dataset during startup, request handling or automated tests.

Import is an explicit operator action that accepts either:

- a local GeoJSON file, or
- an explicit download command that writes a local source artifact before validation.

The importer records:

- source URL,
- dataset title,
- publisher,
- licence,
- edition year,
- retrieval timestamp,
- SHA-256 checksum,
- feature count,
- importer contract version.

## Validation contract

The importer fails closed unless all of the following hold:

- root object type is `FeatureCollection`,
- every item is a GeoJSON `Feature`,
- geometry type is `Polygon` or `MultiPolygon`,
- coordinates are finite numbers,
- longitude is within -180 to 180,
- latitude is within -90 to 90,
- each feature has a stable external identifier,
- each feature has a non-empty display name,
- normalized external identifiers are unique,
- normalized display names are unique,
- feature count matches the explicitly supported dataset edition,
- required upstream fields match the documented source schema.

Schema drift must produce an actionable error rather than silently mapping unknown fields.

## Storage contract

The normalized geographic artifact is independent of MapLibre and contains:

- stable boundary identifier,
- display name,
- boundary type,
- source metadata reference,
- GeoJSON geometry,
- calculated bounding box.

MapLibre is a presentation adapter. It must not define persistence or validation rules.

## Repository policy

- Commit only small, attributed fixtures required for deterministic tests.
- Do not commit the full upstream dataset until repository-size, update and attribution implications are reviewed.
- CI remains network-free.
- Production imports are repeatable and idempotent.
- Attribution is shown in the UI and included in geographic export metadata.

## Consequences

### Positive

- Operational territories align with current administrative areas.
- Tests remain deterministic and independent of an external ArcGIS endpoint.
- Source provenance and licensing remain auditable.
- The domain contract stays independent from the map renderer.

### Trade-offs

- An explicit import step is required before the full map can be populated.
- Dataset edition changes require a reviewed contract update.
- County-level reporting requires a later secondary layer or reconciliation table.

## Next implementation steps

1. Add typed GeoJSON domain models and validation errors.
2. Add a small attributed fixture containing representative Polygon and MultiPolygon records.
3. Implement the pure validation and normalization service.
4. Add import metadata and idempotency tests.
5. Decide whether normalized geometry is stored in SQLite or as a versioned local artifact.
6. Expose a read-only boundary API.
7. Add MapLibre rendering and region selection.
