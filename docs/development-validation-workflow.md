# Development and validation workflow

LEADS uses a two-stage validation model so feature work can move quickly without weakening the merge standard.

## 1. Build a complete batch before the first push

For each issue, implement the smallest meaningful vertical slice as one coherent batch whenever the available development environment supports local editing and testing.

Before the first branch push, include the related:

- domain or data model changes;
- backend routes and services;
- frontend behavior;
- focused tests;
- browser acceptance for user-visible behavior;
- documentation and fixtures.

Run the relevant local lint, format, type, test, build, and focused browser commands before publishing the batch. Avoid pushing one file or one mechanical correction at a time. Connector-only recovery work may require sequential remote writes, but it should still be treated as one conceptual batch and squash-merged.

## 2. Draft pull requests use fast CI

Open new feature pull requests as drafts.

Every draft push runs `CI`, which contains only:

- backend Ruff;
- backend formatting;
- strict mypy;
- backend tests;
- frontend lint;
- frontend unit tests;
- frontend production build.

Feature-specific workflows run only when their declared paths change.

The full Linux and Windows Playwright regression does not run while the pull request remains a draft.

## 3. Ready pull requests use final validation

Mark a pull request ready only when implementation and focused checks are complete.

`Final Validation` runs when:

- a pull request is marked ready for review;
- a new commit is pushed to a ready pull request;
- a ready pull request is reopened;
- the workflow is dispatched manually;
- a commit is pushed to `main` or `master`.

Final validation contains the complete Linux and Windows Playwright regression and screenshot artifacts.

## 4. Merge rule

A pull request may be merged only when the exact current head has:

1. successful fast CI;
2. successful applicable focused workflows;
3. successful final validation;
4. reviewed screenshots for changed user-visible behavior;
5. no unresolved review threads.

Any code change after final validation invalidates the earlier evidence and requires the ready-PR final workflow to pass again.

## 5. Path-filter rule

A focused workflow must include:

- its implementation files;
- focused tests and fixtures;
- its browser or CLI acceptance script;
- its own workflow file.

Do not add broad repository paths unless the feature genuinely depends on them. The general fast CI and ready-PR final validation remain the safety net for cross-feature regressions.
