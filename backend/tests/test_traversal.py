from backend.leadmap.browser.sessions import VisibleCandidate
from backend.leadmap.browser.traversal import (
    OrderedCardAccumulator,
    TraversalLimits,
    TraversalStopReason,
)


def _candidate(provider_key: str, name: str) -> VisibleCandidate:
    return VisibleCandidate(
        candidate_id="",
        provider_key=provider_key,
        displayed_name=name,
        normalized_name="",
    )


def test_accumulator_preserves_first_seen_order_and_rank() -> None:
    accumulator = OrderedCardAccumulator(
        query_text="accountant Kildare",
        query_sequence=2,
        limits=TraversalLimits(max_cards=10),
    )

    assert (
        accumulator.add_batch(
            [_candidate("a", "Alpha"), _candidate("b", "Beta")],
            scroll_step=0,
            captured_at="2026-07-24T18:00:00Z",
        )
        == 2
    )
    assert (
        accumulator.add_batch(
            [_candidate("b", "Beta duplicate"), _candidate("c", "Gamma")],
            scroll_step=1,
            captured_at="2026-07-24T18:00:01Z",
        )
        == 1
    )

    observations = accumulator.observations
    assert [item.candidate.provider_key for item in observations] == ["a", "b", "c"]
    assert [item.result_rank for item in observations] == [1, 2, 3]
    assert [item.first_seen_scroll_step for item in observations] == [0, 0, 1]
    assert all(item.query_text == "accountant Kildare" for item in observations)
    assert all(item.query_sequence == 2 for item in observations)


def test_accumulator_stops_after_stagnant_scrolls() -> None:
    accumulator = OrderedCardAccumulator(
        query_text="accountant Kildare",
        query_sequence=1,
        limits=TraversalLimits(max_stagnant_scrolls=2),
    )
    accumulator.add_batch(
        [_candidate("a", "Alpha")],
        scroll_step=0,
        captured_at="2026-07-24T18:00:00Z",
    )
    accumulator.add_batch(
        [_candidate("a", "Alpha")],
        scroll_step=1,
        captured_at="2026-07-24T18:00:01Z",
    )
    accumulator.add_batch(
        [_candidate("a", "Alpha")],
        scroll_step=2,
        captured_at="2026-07-24T18:00:02Z",
    )

    stop_reason = accumulator.evaluate_stop(scroll_step=2, elapsed_seconds=2)
    assert stop_reason is TraversalStopReason.NO_NEW_RESULTS


def test_accumulator_enforces_card_limit() -> None:
    accumulator = OrderedCardAccumulator(
        query_text="accountant Kildare",
        query_sequence=1,
        limits=TraversalLimits(max_cards=2),
    )
    accumulator.add_batch(
        [_candidate("a", "Alpha"), _candidate("b", "Beta"), _candidate("c", "Gamma")],
        scroll_step=0,
        captured_at="2026-07-24T18:00:00Z",
    )

    assert len(accumulator.observations) == 2
    stop_reason = accumulator.evaluate_stop(scroll_step=0, elapsed_seconds=0)
    assert stop_reason is TraversalStopReason.MAX_CARDS


def test_stop_reason_precedence_is_deterministic() -> None:
    accumulator = OrderedCardAccumulator(
        query_text="accountant Kildare",
        query_sequence=1,
        limits=TraversalLimits(max_cards=1, max_scrolls=0, max_elapsed_seconds=1),
    )
    accumulator.add_batch(
        [_candidate("a", "Alpha")],
        scroll_step=0,
        captured_at="2026-07-24T18:00:00Z",
    )

    assert (
        accumulator.evaluate_stop(
            scroll_step=0,
            elapsed_seconds=1,
            operator_stop=True,
            provider_error=True,
            end_of_list=True,
        )
        is TraversalStopReason.OPERATOR_STOP
    )


def test_limits_reject_invalid_values() -> None:
    invalid_factories = [
        lambda: TraversalLimits(max_cards=0),
        lambda: TraversalLimits(max_scrolls=-1),
        lambda: TraversalLimits(max_elapsed_seconds=0),
        lambda: TraversalLimits(max_stagnant_scrolls=0),
    ]

    for factory in invalid_factories:
        try:
            factory()
        except ValueError:
            continue
        raise AssertionError("Expected invalid traversal limits to raise ValueError.")
