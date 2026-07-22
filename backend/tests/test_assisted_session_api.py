from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.leadmap.api.routes import get_assisted_session_manager
from backend.leadmap.browser import AssistedSessionManager
from backend.leadmap.main import app


class FakeProvider:
    def __init__(self) -> None:
        self.launches: list[str] = []
        self.stop_count = 0

    def launch(self, *, start_url: str) -> None:
        self.launches.append(start_url)

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
