from enum import StrEnum


class QualificationStatus(StrEnum):
    NEW = "new"
    NEEDS_REVIEW = "needs_review"
    QUALIFIED = "qualified"
    SHORTLISTED = "shortlisted"
    SENT_TO_VERIDRA = "sent_to_veridra"
    VERIDRA_REVIEWED = "veridra_reviewed"
    APPROVED_FOR_OUTREACH = "approved_for_outreach"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERSATION = "conversation"
    PROPOSAL = "proposal"
    CUSTOMER = "customer"
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
