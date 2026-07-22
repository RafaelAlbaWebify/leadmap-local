import pytest

from backend.leadmap.browser import (
    AssistedSessionConflict,
    AssistedSessionManager,
    AssistedSessionState,
    AssistedSessionTransitionError,
)


class FakeProvider:
    def __init__(self, *, fail_launch: bool = False) -> None:
        self.fail_launch = fail_launch
        self.launches: list[str] = []
        self.stop_count = 0

    def launch(self, *, start_url: str) -> None:
        self.launches.append(start_url)
        if self.fail_launch:
            raise RuntimeError("launch failed")

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
