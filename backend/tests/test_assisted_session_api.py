from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.leadmap.api.routes import get_assisted_session_manager
from backend.leadmap.browser import (
    AssistedSessionManager,
    OrderedCardAccumulator,
    TraversalLimits,
    TraversalStopReason,
    VisibleCandidate,
)
from backend.leadmap.main import app


class FakeProvider:
    def __init__(self) -> None:
        self.launches: list[str] = []
        self.stop_count = 0
        self.fail_capture = False
        self.fail_collect = False

    def launch(self, *, start_url: str) -> None:
        self.launches.append(start_url)

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
        if self.fail_capture:
            raise RuntimeError("capture exploded")
        return []

    def collect_bounded(
        self,
        *,
        query_text: str,
        query_sequence: int,
        limits: TraversalLimits,
    ):
        if self.fail_collect:
            raise RuntimeError("collection exploded")
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
                    source_url="https://www.google.com/maps/place/West+Coast+Accountancy",
                )
            ],
            scroll_step=0,
            captured_at="2026-07-24T18:00:00Z",
        )
        return accumulator.result(
            scroll_step=3,
            elapsed_seconds=2.25,
            stop_reason=TraversalStopReason.NO_NEW_RESULTS,
        )

    def stop(self) -> None:
        self.stop_count += 1


@pytest.fixture
def assisted_client(client: TestClient) -> Iterator[tuple[TestClient, FakeProvider]]:
    provider = FakeProvider()
    manager = AssistedSessionManager(provider)
    app.dependency_overrides[get_assisted_session_manager] = lambda: manager
    yield client, provider


def _plan_ids(client: TestClient) -> tuple[str, str]:
    seed_response = client.post("/api/v1/seed/ireland")
    assert seed_response.status_code == 200
    territory = client.get("/api/v1/territories").json()[0]
    template = client.get(
        f"/api/v1/query-templates?country_code={territory['country_code']}"
    ).json()[0]
    return territory["id"], template["id"]


def _launch_ready_session(client: TestClient) -> str:
    territory_id, template_id = _plan_ids(client)
    launched = client.post(
        "/api/v1/discovery/session",
        json={
            "territory_id": territory_id,
            "query_template_id": template_id,
            "max_results_per_query": 20,
        },
    )
    assert launched.status_code == 201
    session_id = launched.json()["session_id"]
    ready = client.post(f"/api/v1/discovery/session/{session_id}/ready")
    assert ready.status_code == 200
    return session_id


def test_explicit_launch_ready_status_and_stop(
    assisted_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = assisted_client
    territory_id, template_id = _plan_ids(client)

    assert client.get("/api/v1/discovery/session").json()["state"] == "idle"

    launched = client.post(
        "/api/v1/discovery/session",
        json={
            "territory_id": territory_id,
            "query_template_id": template_id,
            "max_results_per_query": 20,
        },
    )
    assert launched.status_code == 201
    session = launched.json()
    assert session["state"] == "awaiting_operator"
    assert session["session_id"]
    assert provider.launches[0].startswith("https://www.google.com/maps/search/")

    second_launch = client.post(
        "/api/v1/discovery/session",
        json={"territory_id": territory_id, "query_template_id": template_id},
    )
    assert second_launch.status_code == 409

    ready = client.post(f"/api/v1/discovery/session/{session['session_id']}/ready")
    assert ready.status_code == 200
    assert ready.json()["state"] == "ready"

    stopped = client.delete(f"/api/v1/discovery/session/{session['session_id']}")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "stopped"
    assert provider.stop_count == 1

    stopped_again = client.delete(f"/api/v1/discovery/session/{session['session_id']}")
    assert stopped_again.status_code == 200
    assert provider.stop_count == 1


def test_collect_bounded_returns_progress_stop_reason_and_provenance(
    assisted_client: tuple[TestClient, FakeProvider],
) -> None:
    client, _provider = assisted_client
    session_id = _launch_ready_session(client)

    response = client.post(
        f"/api/v1/discovery/session/{session_id}/collect-bounded",
        params={"query_text": "accountant Galway", "query_sequence": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "review"
    assert payload["traversal_stop_reason"] == "no_new_results"
    assert payload["traversal_progress"] == {
        "query_text": "accountant Galway",
        "query_sequence": 2,
        "scroll_step": 3,
        "unique_cards": 1,
        "stagnant_scrolls": 0,
        "elapsed_seconds": 2.25,
        "stop_reason": "no_new_results",
    }
    candidate = payload["candidates"][0]
    assert candidate["displayed_name"] == "West Coast Accountancy"
    assert candidate["query_text"] == "accountant Galway"
    assert candidate["query_sequence"] == 2
    assert candidate["result_rank"] == 1
    assert candidate["first_seen_scroll_step"] == 0
    assert candidate["captured_at"] == "2026-07-24T18:00:00Z"


def test_collect_bounded_requires_ready_session(
    assisted_client: tuple[TestClient, FakeProvider],
) -> None:
    client, _provider = assisted_client
    territory_id, template_id = _plan_ids(client)
    launched = client.post(
        "/api/v1/discovery/session",
        json={"territory_id": territory_id, "query_template_id": template_id},
    )
    session_id = launched.json()["session_id"]

    response = client.post(
        f"/api/v1/discovery/session/{session_id}/collect-bounded",
        params={"query_text": "accountant Galway"},
    )

    assert response.status_code == 409
    assert "marks the browser ready" in response.json()["detail"]


def test_visible_capture_provider_failure_returns_502_and_restores_ready(
    assisted_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = assisted_client
    session_id = _launch_ready_session(client)
    provider.fail_capture = True

    response = client.post(f"/api/v1/discovery/session/{session_id}/capture-visible")

    assert response.status_code == 502
    assert "capture exploded" in response.json()["detail"]
    assert client.get("/api/v1/discovery/session").json()["state"] == "ready"


def test_bounded_collection_provider_failure_returns_502_and_restores_ready(
    assisted_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = assisted_client
    session_id = _launch_ready_session(client)
    provider.fail_collect = True

    response = client.post(
        f"/api/v1/discovery/session/{session_id}/collect-bounded",
        params={"query_text": "accountant Galway"},
    )

    assert response.status_code == 502
    assert "collection exploded" in response.json()["detail"]
    status_response = client.get("/api/v1/discovery/session").json()
    assert status_response["state"] == "ready"
    assert status_response["error"] == "collection exploded"


def test_launch_fails_closed_for_invalid_plan_and_limit(
    assisted_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = assisted_client
    territory_id, template_id = _plan_ids(client)

    too_many = client.post(
        "/api/v1/discovery/session",
        json={
            "territory_id": territory_id,
            "query_template_id": template_id,
            "max_results_per_query": 21,
        },
    )
    assert too_many.status_code == 422
    assert provider.launches == []

    missing = client.post(
        "/api/v1/discovery/session",
        json={
            "territory_id": "missing",
            "query_template_id": template_id,
        },
    )
    assert missing.status_code == 404
    assert provider.launches == []
