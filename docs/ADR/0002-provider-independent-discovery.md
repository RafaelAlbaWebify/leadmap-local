# ADR 0002: Provider-independent discovery

Status: Accepted

## Decision

All acquisition implementations conform to a discovery provider interface. The default
provider is an offline fixture provider. Playwright is an assisted, headed adapter.

## Rationale

The consumer Google Maps interface is unstable and not an API contract. Product data,
tests and exports must survive selector changes or removal of that adapter.

## Consequences

- Browser-specific values are normalized before entering the domain.
- No Google selector may appear outside the Playwright adapter.
- Live capture cannot be declared complete without fixtures and diagnostics.
