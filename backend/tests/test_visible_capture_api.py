from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.leadmap.api.routes import get_assisted_session_manager
from backend.leadmap.browser import AssistedSessionManager, VisibleCandidate
from backend.leadmap.main import app


class FakeCaptureProvider:
    def __init__(self) -> None:
        self.stop_count = 0

    def launch(self, *, start_url: str) -> None:
        return None

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
        return [
            VisibleCandidate(
                candidate_id="candidate-1",
                provider_key="place-1",
                displayed_name=" West Coast Accountancy ",
                normalized_name="",
                category="Accountant",
                address_text="Galway",
                website="example.com",
                source_url="https://maps.example/place-1",
                raw_evidence="West Coast Accountancy · Accountant · Galway",
            ),
            VisibleCandidate(
                candidate_id="candidate-duplicate",
                provider_key="place-1",
                displayed_name="West Coast Accountancy",
                normalized_name="",
            ),
        ][:max_results]

    def stop(self) -> None:
        self.stop_count += 1


@pytest.fixture
def capture_client(client: TestClient) -> Iterator[TestClient]:
    manager = AssistedSessionManager(FakeCaptureProvider())
    app.dependency_overrides[get_assisted_session_manager] = lambda: manager
    yield client


def _launch_and_ready(client: TestClient) -> str:
    assert client.post("/api/v1/seed/ireland").status_code == 200
    territory = client.get("/api/v1/territories").json()[0]
    template = client.get(
        f"/api/v1/query-templates?country_code={territory['country_code']}"
    ).json()[0]
    launched = client.post(
        "/api/v1/discovery/session",
        json={
            "territory_id": territory["id"],
            "query_template_id": template["id"],
            "max_results_per_query": 20,
        },
    )
    session_id = launched.json()["session_id"]
    ready = client.post(f"/api/v1/discovery/session/{session_id}/ready")
    assert ready.status_code == 200
    return session_id


def test_capture_visible_results_and_edit_review(capture_client: TestClient) -> None:
    session_id = _launch_and_ready(capture_client)

    captured = capture_client.post(
        f"/api/v1/discovery/session/{session_id}/capture-visible"
    )

    assert captured.status_code == 200
    payload = captured.json()
    assert payload["state"] == "review"
    assert payload["included_count"] == 1
    assert payload["excluded_count"] == 0
    assert payload["candidates"][0]["displayed_name"] == "West Coast Accountancy"
    assert payload["candidates"][0]["website"] == "https://example.com"

    candidate_id = payload["candidates"][0]["candidate_id"]
    excluded = capture_client.patch(
        f"/api/v1/discovery/session/{session_id}/candidates/{candidate_id}",
        json={"included": False},
    )
    assert excluded.status_code == 200
    assert excluded.json()["included_count"] == 0
    assert excluded.json()["excluded_count"] == 1


def test_capture_before_ready_fails_closed(capture_client: TestClient) -> None:
    assert capture_client.post("/api/v1/seed/ireland").status_code == 200
    territory = capture_client.get("/api/v1/territories").json()[0]
    template = capture_client.get(
        "/api/v1/query-templates?country_code=IE"
    ).json()[0]
    launched = capture_client.post(
        "/api/v1/discovery/session",
        json={
            "territory_id": territory["id"],
            "query_template_id": template["id"],
        },
    )

    session_id = launched.json()["session_id"]
    response = capture_client.post(
        f"/api/v1/discovery/session/{session_id}/capture-visible"
    )
    assert response.status_code == 409
