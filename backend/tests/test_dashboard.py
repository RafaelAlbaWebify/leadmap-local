from fastapi.testclient import TestClient


def test_dashboard_contract_contains_freshness_and_dates(client: TestClient) -> None:
    payload = client.get("/api/v1/dashboard").json()
    assert payload["total_businesses"] == 3
    assert payload["territories"] == 3
    assert payload["recent_leads"]
    lead = payload["recent_leads"][0]
    assert "last_observed_at" in lead
    assert "freshness" in lead
    assert "qualification_status" in lead
