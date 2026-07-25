from collections.abc import Iterator
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from backend.leadmap.api.routes import get_assisted_session_manager
from backend.leadmap.browser import AssistedSessionManager
from backend.leadmap.main import app


class FakeProvider:
    def __init__(self) -> None:
        self.launches: list[str] = []

    def launch(self, *, start_url: str) -> None:
        self.launches.append(start_url)

    def stop(self) -> None:
        pass


@pytest.fixture
def prepared_client(client: TestClient) -> Iterator[tuple[TestClient, FakeProvider]]:
    provider = FakeProvider()
    app.dependency_overrides[get_assisted_session_manager] = lambda: (
        AssistedSessionManager(provider)
    )
    yield client, provider


def _prepared_ids(client: TestClient) -> tuple[str, str]:
    seed = client.post("/api/v1/seed/ireland")
    assert seed.status_code == 200
    territory = client.get("/api/v1/territories").json()[0]
    template = client.post(
        "/api/v1/query-templates",
        json={
            "name": "Prepared Accountancy",
            "sector": "Professional Services",
            "countries": ["IE"],
            "phrases": ["accountant", "tax advisor"],
        },
    )
    assert template.status_code == 201
    return territory["id"], template.json()["id"]


def test_prepared_plan_returns_canonical_sequence(
    prepared_client: tuple[TestClient, FakeProvider],
) -> None:
    client, _ = prepared_client
    territory_id, template_id = _prepared_ids(client)

    response = client.post(
        "/api/v1/discovery/prepared-plan",
        json={
            "territory_id": territory_id,
            "query_template_id": template_id,
            "max_results_per_query": 20,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_planned_queries"] == 2
    assert payload["prepared_queries"] == [
        {
            "sequence": 1,
            "phrase": "accountant",
            "query_text": f"accountant in {payload['territory_name']}, IE",
        },
        {
            "sequence": 2,
            "phrase": "tax advisor",
            "query_text": f"tax advisor in {payload['territory_name']}, IE",
        },
    ]


def test_launches_the_explicitly_selected_prepared_query(
    prepared_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = prepared_client
    territory_id, template_id = _prepared_ids(client)

    response = client.post(
        "/api/v1/discovery/prepared-session",
        json={
            "territory_id": territory_id,
            "query_template_id": template_id,
            "max_results_per_query": 20,
            "query_sequence": 2,
        },
    )

    assert response.status_code == 201
    assert len(provider.launches) == 1
    assert "tax+advisor+in+" in provider.launches[0]
    assert "accountant" not in unquote(provider.launches[0])


def test_rejects_a_query_sequence_outside_the_prepared_plan(
    prepared_client: tuple[TestClient, FakeProvider],
) -> None:
    client, provider = prepared_client
    territory_id, template_id = _prepared_ids(client)

    response = client.post(
        "/api/v1/discovery/prepared-session",
        json={
            "territory_id": territory_id,
            "query_template_id": template_id,
            "query_sequence": 3,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Query sequence must be between 1 and 2."
    assert provider.launches == []
