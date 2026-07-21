# LeadMap Local

LeadMap Local is a local-first workspace for mapping Irish local-authority territories, assigning coverage, and tracking business discovery work.

## Development setup

```powershell
.\scripts\bootstrap.ps1
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

The official Tailte Éireann ArcGIS layer contains 9,161 polygon fragments. The setup command downloads them in pages, groups them by `ENG_NAME_VALUE` into Ireland's 31 local authorities, converts each authority to a normalized `MultiPolygon`, validates every geometry, records provenance and retrieval time, calculates a SHA-256 checksum, and writes a checksum-addressed artifact under `data/geography`. Repeating the command with unchanged normalized source data is idempotent.

The application itself performs no runtime geography download. Tests and CI remain network-free.

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
