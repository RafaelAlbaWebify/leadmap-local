# Aggregate query review

The aggregate review combines completed bounded-query reviews without losing source provenance.

## Rules

- Provider identity is the primary cross-query key.
- Normalized business name plus phone, website, or address is the fallback key.
- First-seen business order is preserved.
- Every query sequence and result rank remains attached to the business.
- Duplicate appearances are counted rather than discarded.
- A business is included by default when at least one retained appearance is included.
- Duplicate query sequences and incomplete query/rank provenance are rejected.

## Current scope

This slice is frontend-only and in-memory. It does not persist businesses, create deals, send outreach, or run additional browser searches.
