# Contributing to LeadMap

LeadMap uses this repository-native workflow:

`scope ledger → branch → implementation → tests → pull request → exact-head CI → review → merge → post-merge verification`

The repository, not chat history, is the source of truth.

## Before coding

Create a scope ledger from `docs/development/SCOPE_LEDGER_TEMPLATE.md`. Record the base commit, required work, optional work, user-visible outcome, non-goals, proof and rollback. Inspect relevant source, tests, workflows, documentation contracts and open pull requests. Do not invent paths, commands, APIs or dependencies.

## Branch and PR discipline

- Never force-update `main`.
- Use a focused branch from a verified base commit.
- Keep one coherent vertical slice per PR.
- Complete `.github/pull_request_template.md`.
- Inspect changed filenames and the final diff.
- Use an expected-head SHA guard when merging.
- A new head commit invalidates earlier CI conclusions.

## Required checks

Backend:

```bash
python -m ruff check backend
python -m ruff format --check backend
python -m mypy
pytest -q
```

Frontend:

```bash
cd frontend
npm ci --no-audit --no-fund
npm run lint
npm run test
npm run build
```

CI is the authoritative automatic proof for the exact PR head.

## Test integrity

Classify a failure before editing: implementation, test, fixture, environment or workflow/configuration. Do not delete, skip or weaken a test merely to make CI green. Preserve its intended protection and explain corrected assertions.

## Documentation contracts

Before substantially changing README, setup, migration, release or command documentation, search for tests, workflows, scripts and external references that depend on headings, commands, paths, fixtures, links or versions. Update those contracts deliberately.

## UI and real-environment proof

Rendering and browser tests are not visual acceptance. UI PRs must define target widths, important states and accessibility checks, then inspect full-resolution screenshots. Windows/browser acceptance remains required when environment-specific behavior matters.

## Safety

- Keep startup and CI network-free where designed.
- Use synthetic or redacted public fixtures.
- Do not commit credentials, personal data or private infrastructure.
- No unattended scraping, CAPTCHA handling, proxy rotation or anti-detection behavior.
- Prefer explicit operator-controlled actions and dry runs.

## Completion reporting

Report separately: Implemented, Automatically verified, Artifact-reviewed, Manually reviewed, User accepted, Merged, Released and Publicly verified. List exact remaining gates.

## Post-merge hygiene

Verify the resulting `main` commit, open PRs/issues, documentation state and whether any release/deployment workflow ran unexpectedly. Close superseded work and remove temporary artifacts.