from pathlib import Path

from fastapi.testclient import TestClient

from backend.leadmap.api.geography_routes import get_geographic_artifact_directory
from backend.leadmap.geography import TerritoryBoundaryLink, store_territory_boundary_link
from backend.leadmap.main import app


def _territory_id(client: TestClient) -> str:
    response = client.post(
        "/api/v1/territories",
        json={
            "name": "Galway City",
            "country_code": "IE",
            "administrative_area": "County Galway",
            "locality": "Galway",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def test_returns_never_verified_coverage_for_link_without_leads(
    client: TestClient,
    tmp_path: Path,
) -> None:
    territory_id = _territory_id(client)
    store_territory_boundary_link(
        TerritoryBoundaryLink(
            territory_id=territory_id,
            checksum_sha256="a" * 64,
            boundary_external_id="la-galway-city",
            boundary_name="Galway City",
        ),
        directory=tmp_path,
    )
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/coverage")

    assert response.status_code == 200
    assert response.json() == [
        {
            "territory_id": territory_id,
            "territory_name": "Galway City",
            "checksum_sha256": "a" * 64,
            "boundary_external_id": "la-galway-city",
            "boundary_name": "Galway City",
            "lead_count": 0,
            "latest_observed_at": None,
            "freshness": "never_verified",
        }
    ]


def test_fails_closed_when_link_references_missing_territory(
    client: TestClient,
    tmp_path: Path,
) -> None:
    store_territory_boundary_link(
        TerritoryBoundaryLink(
            territory_id="missing-territory",
            checksum_sha256="b" * 64,
            boundary_external_id="la-cork-city",
            boundary_name="Cork City",
        ),
        directory=tmp_path,
    )
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/coverage")

    assert response.status_code == 422
    assert response.json()["detail"] == "Territory link references a missing territory."
