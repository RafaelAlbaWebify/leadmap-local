from enum import StrEnum


class QualificationStatus(StrEnum):
    NEW = "new"
    NEEDS_REVIEW = "needs_review"
    QUALIFIED = "qualified"
    UNSUITABLE = "unsuitable"
    DUPLICATE = "duplicate"
    ARCHIVED = "archived"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    AGEING = "ageing"
    STALE = "stale"
    NEVER_VERIFIED = "never_verified"


class SearchRunStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
