from datetime import UTC, datetime

from .enums import FreshnessStatus


def calculate_freshness(
    last_verified_at: datetime | None,
    *,
    ageing_after_days: int = 30,
    stale_after_days: int = 90,
    now: datetime | None = None,
) -> FreshnessStatus:
    if last_verified_at is None:
        return FreshnessStatus.NEVER_VERIFIED

    current = now or datetime.now(UTC)
    age_days = (current - last_verified_at).days

    if age_days >= stale_after_days:
        return FreshnessStatus.STALE
    if age_days >= ageing_after_days:
        return FreshnessStatus.AGEING
    return FreshnessStatus.FRESH
