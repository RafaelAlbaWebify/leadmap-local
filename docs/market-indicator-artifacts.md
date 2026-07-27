# Market indicator artifacts

LEADS does not download or infer market indicators at runtime. An operator must review and approve a public dataset before converting it to the versioned JSON contract and installing it locally.

## Required source metadata

Every artifact must include the dataset title, publisher, public source URL, licence, publication date and retrieval timestamp. Each record must identify an exact territory key, sector key, indicator key, unit and finite numeric value. Missing values must be omitted rather than estimated.

## Approval checklist

1. Confirm the publisher is an official or otherwise approved public-data authority.
2. Confirm the licence permits local storage and use.
3. Record the exact source URL, publication date and retrieval timestamp.
4. Verify that the source geography maps directly to a configured LEADS territory key.
5. Do not combine incompatible geographic levels or silently allocate regional totals to local territories.
6. Preserve the approved source file separately; the LEADS JSON artifact is a derived import contract.

## Installation

From the repository root:

```text
python scripts/install-market-indicators.py approved-indicators.json
```

Use `--directory` to override the default `data/market-indicators` location. Installation validates the complete document, calculates the canonical SHA-256 checksum and writes one immutable checksum-addressed JSON file. Reinstalling identical content is idempotent. Invalid, duplicate, non-finite or checksum-mismatched content fails closed.

## Runtime API

- `GET /api/v1/market-indicators/artifacts`
- `GET /api/v1/market-indicators/artifacts/{checksum}/territories/{territory_key}`
- Optional query: `sector_key`

Every value response includes its source metadata and checksum. An empty response means no compatible value is installed; it must not be interpreted as zero.
