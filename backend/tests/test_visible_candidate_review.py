import pytest

from backend.leadmap.browser import (
    AssistedSessionManager,
    AssistedSessionState,
    AssistedSessionTransitionError,
    VisibleCandidate,
    normalize_and_deduplicate_candidates,
)


class FakeCaptureProvider:
    def __init__(self, candidates: list[VisibleCandidate]) -> None:
        self.candidates = candidates
        self.capture_limits: list[int] = []
        self.stop_count = 0

    def launch(self, *, start_url: str) -> None:
        return None

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
        self.capture_limits.append(max_results)
        return self.candidates

    def stop(self) -> None:
        self.stop_count += 1


def candidate(
    candidate_id: str,
    provider_key: str,
    name: str,
    *,
    phone: str | None = None,
    website: str | None = None,
    address: str | None = None,
) -> VisibleCandidate:
    return VisibleCandidate(
        candidate_id=candidate_id,
        provider_key=provider_key,
        displayed_name=name,
        normalized_name="",
        phone=phone,
        website=website,
        address_text=address,
    )


def test_normalizes_deduplicates_and_caps_visible_candidates() -> None:
    normalized = normalize_and_deduplicate_candidates(
        [
            candidate(
                "one",
                " provider-1 ",
                "  West   Coast Accountancy ",
                phone=" +353 91 000 001 ",
                website="Example.COM/",
            ),
            candidate(
                "duplicate-provider",
                "provider-1",
                "Different label",
            ),
            candidate(
                "duplicate-identity",
                "provider-2",
                "West Coast Accountancy",
                phone="+353 91 000 001",
                website="https://example.com",
            ),
            candidate("two", "provider-3", "Harbour Legal", address=" Dublin  2 "),
            candidate("three", "provider-4", "Third candidate"),
        ],
        max_results=2,
    )

    assert [item.candidate_id for item in normalized] == ["one", "two"]
    assert normalized[0].displayed_name == "West Coast Accountancy"
    assert normalized[0].normalized_name == "west coast accountancy"
    assert normalized[0].website == "https://example.com"
    assert normalized[1].address_text == "Dublin 2"


def test_capture_requires_ready_and_enters_review() -> None:
    provider = FakeCaptureProvider(
        [
            candidate("one", "provider-1", "West Coast Accountancy"),
            candidate("two", "provider-2", "Harbour Legal"),
        ]
    )
    manager = AssistedSessionManager(provider)
    session = manager.launch(territory_id="territory-1", query_template_id="template-1")

    with pytest.raises(AssistedSessionTransitionError, match="marks the browser ready"):
        manager.capture_visible(session.session_id or "", max_results=20)

    manager.mark_ready(session.session_id or "")
    review = manager.capture_visible(session.session_id or "", max_results=1)

    assert review.state is AssistedSessionState.REVIEW
    assert len(review.candidates) == 1
    assert provider.capture_limits == [1]

    updated = manager.set_candidate_included(
        session.session_id or "",
        review.candidates[0].candidate_id,
        included=False,
    )
    assert updated.candidates[0].included is False


def test_failed_capture_returns_to_ready_without_partial_candidates() -> None:
    class FailingProvider(FakeCaptureProvider):
        def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
            raise RuntimeError("selector drift")

    manager = AssistedSessionManager(FailingProvider([]))
    session = manager.launch(territory_id="territory-1", query_template_id="template-1")
    manager.mark_ready(session.session_id or "")

    with pytest.raises(RuntimeError, match="selector drift"):
        manager.capture_visible(session.session_id or "", max_results=20)

    snapshot = manager.snapshot()
    assert snapshot.state is AssistedSessionState.READY
    assert snapshot.error == "selector drift"
    assert snapshot.candidates == ()
