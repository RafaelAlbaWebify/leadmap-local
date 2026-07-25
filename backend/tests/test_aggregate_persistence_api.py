from fastapi.testclient import TestClient


def _seed_workspace(client: TestClient) -> tuple[str, str]:
    territory = client.post(
        "/api/v1/territories",
        json={
            "name": "Kildare County",
            "country_code": "IE",
            "administrative_area": "County Kildare",
            "locality": None,
        },
    )
    assert territory.status_code == 201
    template = client.post(
        "/api/v1/query-templates",
        json={
            "name": "Accountancy",
            "sector": "Professional Services",
            "countries": ["IE"],
            "phrases": ["accountant", "tax advisor"],
        },
    )
    assert template.status_code == 201
    return territory.json()["id"], template.json()["id"]


def _payload(territory_id: str, template_id: str) -> dict[str, object]:
    return {
        "batch_id": "batch-kildare-accountancy-1",
        "territory_id": territory_id,
        "query_template_id": template_id,
        "businesses": [
            {
                "displayed_name": "Kildare Accountancy",
                "normalized_name": "kildare accountancy",
                "category": "Accountant",
                "address_text": "Kildare County",
                "phone": "+353 45 000 001",
                "website": "https://kildare-accountancy.example",
                "latitude": "53.15",
                "longitude": "-6.91",
                "provider_key": "place-1",
                "included": True,
                "observations": [
                    {
                        "query_text": "accountant in Kildare County, IE",
                        "query_sequence": 1,
                        "result_rank": 1,
                        "first_seen_scroll_step": 0,
                        "captured_at": "2026-07-25T08:00:00Z",
                        "source_url": "https://maps.example/place-1",
                        "raw_evidence": "Kildare Accountancy · Accountant",
                        "candidate_id": "candidate-1-1",
                    },
                    {
                        "query_text": "tax advisor in Kildare County, IE",
                        "query_sequence": 2,
                        "result_rank": 3,
                        "first_seen_scroll_step": 1,
                        "captured_at": "2026-07-25T08:05:00Z",
                        "source_url": "https://maps.example/place-1",
                        "raw_evidence": "Kildare Accountancy · Accountant",
                        "candidate_id": "candidate-2-3",
                    },
                ],
            },
            {
                "displayed_name": "Excluded Books",
                "normalized_name": "excluded books",
                "category": "Bookkeeper",
                "address_text": "Kildare County",
                "phone": None,
                "website": None,
                "latitude": None,
                "longitude": None,
                "provider_key": "place-excluded",
                "included": False,
                "observations": [
                    {
                        "query_text": "accountant in Kildare County, IE",
                        "query_sequence": 1,
                        "result_rank": 8,
                        "first_seen_scroll_step": 2,
                        "captured_at": "2026-07-25T08:01:00Z",
                        "source_url": "https://maps.example/place-excluded",
                        "raw_evidence": "Excluded Books",
                        "candidate_id": "candidate-excluded",
                    }
                ],
            },
        ],
    }


def test_saves_only_included_businesses_and_preserves_multiple_observations(
    client: TestClient,
) -> None:
    territory_id, template_id = _seed_workspace(client)
    response = client.post(
        "/api/v1/discovery/aggregate-businesses",
        json=_payload(territory_id, template_id),
    )

    assert response.status_code == 201
    assert response.json() == {
        "businesses_created": 1,
        "businesses_matched": 0,
        "observations_created": 2,
        "observations_skipped": 0,
        "businesses_skipped": 1,
    }
    leads = client.get("/api/v1/leads").json()
    assert len(leads) == 2
    assert {item["name"] for item in leads} == {"Kildare Accountancy"}


def test_repeated_batch_submission_is_idempotent(client: TestClient) -> None:
    territory_id, template_id = _seed_workspace(client)
    payload = _payload(territory_id, template_id)
    first = client.post("/api/v1/discovery/aggregate-businesses", json=payload)
    second = client.post("/api/v1/discovery/aggregate-businesses", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == {
        "businesses_created": 0,
        "businesses_matched": 1,
        "observations_created": 0,
        "observations_skipped": 2,
        "businesses_skipped": 1,
    }


def test_rejects_ambiguous_fallback_identity(client: TestClient) -> None:
    territory_id, template_id = _seed_workspace(client)
    payload = _payload(territory_id, template_id)
    business = payload["businesses"][0]
    assert isinstance(business, dict)
    business["provider_key"] = ""
    business["phone"] = None
    business["website"] = None
    business["address_text"] = None

    response = client.post("/api/v1/discovery/aggregate-businesses", json=payload)

    assert response.status_code == 422
    assert "stable phone, website, or address" in response.json()["detail"]
