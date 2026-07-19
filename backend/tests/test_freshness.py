from datetime import UTC, datetime, timedelta

from backend.leadmap.domain.enums import FreshnessStatus
from backend.leadmap.domain.freshness import calculate_freshness


def test_never_verified_is_explicit() -> None:
    assert calculate_freshness(None) is FreshnessStatus.NEVER_VERIFIED


def test_freshness_thresholds() -> None:
    now = datetime(2026, 7, 19, tzinfo=UTC)
    assert calculate_freshness(now - timedelta(days=4), now=now) is FreshnessStatus.FRESH
    assert calculate_freshness(now - timedelta(days=30), now=now) is FreshnessStatus.AGEING
    assert calculate_freshness(now - timedelta(days=90), now=now) is FreshnessStatus.STALE
