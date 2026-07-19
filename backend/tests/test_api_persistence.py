from fastapi.testclient import TestClient


def test_territory_crud_contract(client: TestClient) -> None:
    created = client.post(
        "/api/v1/territories",
        json={
            "name": "Galway City",
            "country_code": "IE",
            "administrative_area": "County Galway",
            "locality": "Galway",
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/territories")
    assert listed.status_code == 200
    assert listed.json()[0]["country_code"] == "IE"


def test_query_template_country_filter(client: TestClient) -> None:
    created = client.post(
        "/api/v1/query-templates",
        json={
            "name": "Accountancy",
            "sector": "Professional Services",
            "countries": ["IE"],
            "phrases": ["accountant", "tax advisor"],
        },
    )
    assert created.status_code == 201
    assert len(client.get("/api/v1/query-templates?country_code=IE").json()) == 1
    assert client.get("/api/v1/query-templates?country_code=US").json() == []


def test_empty_exports_are_downloadable(client: TestClient) -> None:
    csv_response = client.get("/api/v1/exports/leads.csv")
    json_response = client.get("/api/v1/exports/leads.json")
    assert csv_response.status_code == 200
    assert "attachment" in csv_response.headers["content-disposition"]
    assert csv_response.text.startswith("business_id,location_id")
    assert json_response.status_code == 200
    assert json_response.json()["schema_version"] == "1.1"


def test_duplicate_territory_returns_conflict(client: TestClient) -> None:
    payload = {
        "name": "Galway City",
        "country_code": "ie",
        "administrative_area": "County Galway",
        "locality": "Galway",
    }
    assert client.post("/api/v1/territories", json=payload).status_code == 201
    assert client.post("/api/v1/territories", json=payload).status_code == 409


def test_query_template_input_is_normalized(client: TestClient) -> None:
    response = client.post(
        "/api/v1/query-templates",
        json={
            "name": " Accountancy ",
            "sector": " Professional Services ",
            "countries": ["ie", "IE"],
            "phrases": [" accountant ", "accountant", "tax advisor"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["countries"] == ["IE"]
    assert payload["phrases"] == ["accountant", "tax advisor"]
