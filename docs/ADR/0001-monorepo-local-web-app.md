# ADR 0001: Monorepo local web application

Status: Accepted

## Decision

Use a single public repository containing a FastAPI backend and React/Vite frontend.
Run both locally rather than packaging Electron initially.

## Rationale

The map-heavy, filter-heavy workflow benefits from a proper frontend. A local HTTP
boundary keeps the browser collector, database and UI independently testable. Deferring
desktop packaging avoids early complexity.

## Consequences

- Two toolchains must be checked in CI.
- A PowerShell launcher hides setup complexity on Windows.
- Packaging is a later decision after workflow validation.
