# LeadMap engineering operating rules

These rules apply to every automated or human change in this repository.

## Source of truth

- Current repository contents, logs, tests, command output and generated artifacts are authoritative.
- Conversation memory and README claims are context only.
- Never claim implementation, verification, merge, release or public visibility without evidence that directly proves that state.

## Required state labels

Keep these states separate: Proposed, Implemented, Automatically verified, Artifact-reviewed, Manually reviewed, User accepted, Merged, Released and Publicly verified. Do not collapse them into “done”.

## Scope ledger

Before implementation, record the requested outcome, repository and base commit, affected files or subsystems, public surfaces, proof gates, exclusions and completion conditions. Use `docs/development/SCOPE_LEDGER_TEMPLATE.md` and reconcile it before completion.

## Default workflow

1. Inspect the current repository and open work.
2. Define the smallest coherent vertical slice.
3. Define proof before editing.
4. Create an isolated branch from the verified base.
5. Make the smallest relevant change.
6. Add or update tests without weakening protection.
7. Inspect the exact diff.
8. Run CI against the exact PR head SHA.
9. Merge only when every required job passes for that SHA.
10. Re-fetch the merged state and inspect remaining PRs and issues.

## Claim discipline

- A successful write proves a mutation, not correctness.
- Passing tests prove only tested behavior.
- A rendered page is not visual approval.
- A merged PR is not a release.
- Repository metadata does not prove profile pins, rendered pages or logged-out public presentation.
- Label indirect conclusions as inferences.

## Implementation discipline

- Repair the authoritative module instead of stacking patches.
- Avoid unrelated rewrites, broad dependency upgrades and speculative features.
- Fix code before adding lint, formatting, typing or test exceptions.
- Keep domain concepts and interfaces explicit.
- Preserve local-first, deterministic and network-free tests.
- Do not add unattended scraping, CAPTCHA handling, proxy rotation or anti-detection behavior.
- Do not expose secrets, tokens, personal data or private infrastructure.

## Debugging discipline

Record the observed failure, evidence, known facts, unknowns, likely layer, hypothesis, diagnostic proof, smallest patch, rerun result and final state. Do not change or remove a test merely to make CI green; first classify the defect as implementation, test, fixture, environment or workflow.

## CI discipline

- Previous CI does not count after the PR head changes.
- Inspect failed steps and logs before patching.
- Do not merge pending, cancelled, unexpectedly skipped or stale checks.
- Re-run only when a failure is proven transient.
- Avoid rapid repeated polling of unchanged state.

## UI and real-environment acceptance

Automated checks do not replace full-resolution screenshot review or validation on the target OS/browser when paths, fonts, scaling, permissions or local data can alter behavior. Record those gates explicitly.

## Repository hygiene

After a milestone, close superseded work, remove temporary files, verify documentation and the default-branch commit, and confirm no unexpected release or deployment occurred.

Detailed contributor requirements are in `CONTRIBUTING.md`.