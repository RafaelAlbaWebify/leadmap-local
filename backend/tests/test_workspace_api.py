def test_seed_ireland_is_idempotent(client) -> None:
    first = client.post("/api/v1/seed/ireland")
    second = client.post("/api/v1/seed/ireland")

    assert first.status_code == 200
    assert first.json()["territories_created"] == 1
    assert first.json()["query_templates_created"] == 5
    assert second.status_code == 200
    assert second.json()["territories_created"] == 0
    assert second.json()["query_templates_created"] == 0


def test_discovery_plan_uses_persisted_territory_and_template(client) -> None:
    client.post("/api/v1/seed/ireland")
    territories = client.get("/api/v1/territories").json()
    templates = client.get("/api/v1/query-templates?country_code=IE").json()

    response = client.post(
        "/api/v1/discovery/plan",
        json={
            "territory_id": territories[0]["id"],
            "query_template_id": templates[0]["id"],
            "max_results_per_query": 20,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["country_code"] == "IE"
    assert payload["mode"] == "assisted"
    assert payload["total_planned_queries"] == len(payload["phrases"])


def test_discovery_plan_rejects_missing_records(client) -> None:
    response = client.post(
        "/api/v1/discovery/plan",
        json={
            "territory_id": "missing",
            "query_template_id": "missing",
            "max_results_per_query": 20,
        },
    )
    assert response.status_code == 404


def test_leads_endpoint_is_bounded(client) -> None:
    response = client.get("/api/v1/leads?limit=5000")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
