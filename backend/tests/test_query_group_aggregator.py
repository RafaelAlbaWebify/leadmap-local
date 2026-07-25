from backend.leadmap.browser.query_group import QueryGroupAggregator
from backend.leadmap.browser.sessions import VisibleCandidate
from backend.leadmap.browser.traversal import (
    TraversalObservation,
    TraversalProgress,
    TraversalResult,
    TraversalStopReason,
)


def _observation(
    *,
    provider_key: str,
    name: str,
    query_text: str,
    query_sequence: int,
    rank: int,
    phone: str | None = None,
) -> TraversalObservation:
    candidate = VisibleCandidate(
        candidate_id=f"candidate-{query_sequence}-{rank}",
        provider_key=provider_key,
        displayed_name=name,
        normalized_name=name.casefold(),
        phone=phone,
        query_text=query_text,
        query_sequence=query_sequence,
        result_rank=rank,
        first_seen_scroll_step=0,
        captured_at="2026-07-24T19:00:00Z",
    )
    return TraversalObservation(
        candidate=candidate,
        query_text=query_text,
        query_sequence=query_sequence,
        result_rank=rank,
        first_seen_scroll_step=0,
        captured_at="2026-07-24T19:00:00Z",
    )


def _result(
    query_text: str,
    query_sequence: int,
    observations: tuple[TraversalObservation, ...],
) -> TraversalResult:
    return TraversalResult(
        observations=observations,
        progress=TraversalProgress(
            query_text=query_text,
            query_sequence=query_sequence,
            scroll_step=3,
            unique_cards=len(observations),
            stagnant_scrolls=2,
            elapsed_seconds=3.5,
            stop_reason=TraversalStopReason.NO_NEW_RESULTS,
        ),
    )


def test_aggregates_repeated_provider_business_without_losing_query_ranks() -> None:
    aggregator = QueryGroupAggregator()
    first = _observation(
        provider_key="place-1",
        name="Kildare Accountancy",
        query_text="accountant Kildare County",
        query_sequence=1,
        rank=2,
    )
    second = _observation(
        provider_key="place-1",
        name="Kildare Accountancy",
        query_text="tax advisor Kildare County",
        query_sequence=2,
        rank=5,
    )

    aggregator.add_result(_result(first.query_text, 1, (first,)))
    aggregator.add_result(_result(second.query_text, 2, (second,)))
    snapshot = aggregator.snapshot()

    assert snapshot.total_observations == 2
    assert snapshot.unique_businesses == 1
    assert snapshot.duplicate_appearances == 1
    assert snapshot.businesses[0].appearance_count == 2
    assert [item.query_sequence for item in snapshot.businesses[0].observations] == [1, 2]
    assert [item.result_rank for item in snapshot.businesses[0].observations] == [2, 5]


def test_preserves_first_seen_business_order_across_queries() -> None:
    aggregator = QueryGroupAggregator()
    alpha = _observation(
        provider_key="alpha",
        name="Alpha",
        query_text="accountant Kildare County",
        query_sequence=1,
        rank=1,
    )
    beta = _observation(
        provider_key="beta",
        name="Beta",
        query_text="accountant Kildare County",
        query_sequence=1,
        rank=2,
    )
    gamma = _observation(
        provider_key="gamma",
        name="Gamma",
        query_text="bookkeeper Kildare County",
        query_sequence=2,
        rank=1,
    )

    aggregator.add_result(_result(alpha.query_text, 1, (alpha, beta)))
    aggregator.add_result(_result(gamma.query_text, 2, (gamma,)))

    assert [item.representative.displayed_name for item in aggregator.snapshot().businesses] == [
        "Alpha",
        "Beta",
        "Gamma",
    ]
    assert [item.first_seen_order for item in aggregator.snapshot().businesses] == [1, 2, 3]


def test_uses_normalized_fallback_identity_when_provider_key_is_missing() -> None:
    aggregator = QueryGroupAggregator()
    first = _observation(
        provider_key="",
        name="County Books",
        phone="+353 45 000 001",
        query_text="accountant Kildare County",
        query_sequence=1,
        rank=4,
    )
    second = _observation(
        provider_key="",
        name="County Books",
        phone="+353 45 000 001",
        query_text="bookkeeper Kildare County",
        query_sequence=2,
        rank=1,
    )

    aggregator.add_result(_result(first.query_text, 1, (first,)))
    aggregator.add_result(_result(second.query_text, 2, (second,)))

    snapshot = aggregator.snapshot()
    assert snapshot.unique_businesses == 1
    assert snapshot.businesses[0].identity_key.startswith("fallback:county books|")


def test_rejects_duplicate_query_sequence() -> None:
    aggregator = QueryGroupAggregator()
    observation = _observation(
        provider_key="place-1",
        name="Alpha",
        query_text="accountant Kildare County",
        query_sequence=1,
        rank=1,
    )
    result = _result(observation.query_text, 1, (observation,))
    aggregator.add_result(result)

    try:
        aggregator.add_result(result)
    except ValueError as exc:
        assert "already been aggregated" in str(exc)
    else:
        raise AssertionError("Duplicate query sequences must be rejected.")
