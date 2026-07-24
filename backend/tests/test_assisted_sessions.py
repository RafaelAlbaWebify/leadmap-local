import pytest

from backend.leadmap.browser import (
    AssistedSessionConflict,
    AssistedSessionManager,
    AssistedSessionState,
    AssistedSessionTransitionError,
    OrderedCardAccumulator,
    TraversalLimits,
    TraversalStopReason,
    VisibleCandidate,
)


class FakeProvider:
    def __init__(self, *, fail_launch: bool = False, fail_collect: bool = False) -> None:
        self.fail_launch = fail_launch
        self.fail_collect = fail_collect
        self.launches: list[str] = []
        self.stop_count = 0

    def launch(self, *, start_url: str) -> None:
        self.launches.append(start_url)
        if self.fail_launch:
            raise RuntimeError("launch failed")

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
        return []

    def collect_bounded(
        self,
        *,
        query_text: str,
        query_sequence: int,
        limits: TraversalLimits,
    ):
        if self.fail_collect:
            raise RuntimeError("collection failed")
        accumulator = OrderedCardAccumulator(
            query_text=query_text,
            query_sequence=query_sequence,
            limits=limits,
        )
        accumulator.add_batch(
            [
                VisibleCandidate(
                    candidate_id="candidate-1",
                    provider_key="place-1",
                    displayed_name="West Coast Accountancy",
                    normalized_name="",
                )
            ],
            scroll_step=0,
            captured_at="2026-07-24T18:00:00Z",
        )
        return accumulator.result(
            scroll_step=2,
            elapsed_seconds=1.5,
            stop_reason=TraversalStopReason.NO_NEW_RESULTS,
        )

    def stop(self) -> None:
        self.stop_count += 1


def test_requires_explicit_ready_transition_and_idempotent_stop() -> None:
    provider = FakeProvider()
    manager = AssistedSessionManager(provider)

    assert manager.snapshot().state is AssistedSessionState.IDLE

    launched = manager.launch(
        territory_id="territory-1",
        query_template_id="template-1",
    )
    assert launched.state is AssistedSessionState.AWAITING_OPERATOR
    assert provider.launches == ["about:blank"]

    ready = manager.mark_ready(launched.session_id or "")
    assert ready.state is AssistedSessionState.READY

    stopped = manager.stop(ready.session_id)
    assert stopped.state is AssistedSessionState.STOPPED
    assert manager.stop(ready.session_id).state is AssistedSessionState.STOPPED
    assert provider.stop_count == 1


def test_collect_bounded_preserves_progress_and_candidate_provenance() -> None:
    manager = AssistedSessionManager(FakeProvider())
    launched = manager.launch(territory_id="territory-1", query_template_id="template-1")
    ready = manager.mark_ready(launched.session_id or "")

    reviewed = manager.collect_bounded(
        ready.session_id or "",
        query_text="accountant Galway",
        query_sequence=3,
        limits=TraversalLimits(max_cards=10),
    )

    assert reviewed.state is AssistedSessionState.REVIEW
    assert reviewed.traversal_query_text == "accountant Galway"
    assert reviewed.traversal_query_sequence == 3
    assert reviewed.traversal_scroll_step == 2
    assert reviewed.traversal_unique_cards == 1
    assert reviewed.traversal_elapsed_seconds == 1.5
    assert reviewed.traversal_stop_reason == "no_new_results"
    assert reviewed.candidates[0].query_text == "accountant Galway"
    assert reviewed.candidates[0].result_rank == 1
    assert reviewed.candidates[0].first_seen_scroll_step == 0


def test_collect_bounded_restores_ready_state_after_provider_error() -> None:
    provider = FakeProvider(fail_collect=True)
    manager = AssistedSessionManager(provider)
    launched = manager.launch(territory_id="territory-1", query_template_id="template-1")
    ready = manager.mark_ready(launched.session_id or "")

    with pytest.raises(RuntimeError, match="collection failed"):
        manager.collect_bounded(
            ready.session_id or "",
            query_text="accountant Galway",
            query_sequence=1,
            limits=TraversalLimits(),
        )

    snapshot = manager.snapshot()
    assert snapshot.state is AssistedSessionState.READY
    assert snapshot.error == "collection failed"


def test_rejects_second_active_session() -> None:
    manager = AssistedSessionManager(FakeProvider())
    manager.launch(territory_id="territory-1", query_template_id="template-1")

    with pytest.raises(AssistedSessionConflict, match="already active"):
        manager.launch(territory_id="territory-2", query_template_id="template-2")


def test_rejects_invalid_ready_transitions() -> None:
    manager = AssistedSessionManager(FakeProvider())

    with pytest.raises(AssistedSessionTransitionError, match="does not exist"):
        manager.mark_ready("missing")
    launched = manager.launch(territory_id="territory-1", query_template_id="template-1")
    manager.mark_ready(launched.session_id or "")

    with pytest.raises(AssistedSessionTransitionError, match="awaiting the operator"):
        manager.mark_ready(launched.session_id or "")


def test_records_failed_launch_and_allows_later_retry() -> None:
    provider = FakeProvider(fail_launch=True)
    manager = AssistedSessionManager(provider)

    with pytest.raises(RuntimeError, match="launch failed"):
        manager.launch(territory_id="territory-1", query_template_id="template-1")

    assert manager.snapshot().state is AssistedSessionState.FAILED
    assert manager.snapshot().error == "launch failed"

    provider.fail_launch = False
    retried = manager.launch(territory_id="territory-1", query_template_id="template-1")
    assert retried.state is AssistedSessionState.AWAITING_OPERATOR
