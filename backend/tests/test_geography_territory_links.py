from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from backend.leadmap.api.geography_routes import get_geographic_artifact_directory
from backend.leadmap.geography import (
    BoundarySourceMetadata,
    import_boundary_bytes,
    store_boundary_artifact,
)
from backend.leadmap.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "ireland_boundaries_sample.geojson"


def _stored_checksum(directory: Path) -> str:
    artifact = import_boundary_bytes(
        FIXTURE.read_bytes(),
        source=BoundarySourceMetadata(
            dataset_title="Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
            publisher="Tailte Éireann",
            licence="CC BY 4.0",
            edition_year=2026,
            source_url="https://example.invalid/ireland-local-authorities.geojson",
            retrieved_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
        ),
        id_field="boundary_id",
        name_field="name",
        expected_feature_count=2,
    )
    store_boundary_artifact(artifact, directory=directory)
    return artifact.checksum_sha256


def _territory_id(client: TestClient) -> str:
    response = client.post(
        "/api/v1/territories",
        json={
            "name": "Galway",
            "country_code": "IE",
            "administrative_area": "County Galway",
            "locality": "Galway",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def test_persists_and_lists_validated_territory_link(
    client: TestClient,
    tmp_path: Path,
) -> None:
    checksum = _stored_checksum(tmp_path)
    territory_id = _territory_id(client)
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.put(
        f"/api/v1/geography/territory-links/{territory_id}",
        json={
            "checksum_sha256": checksum,
            "boundary_external_id": "la-galway-city",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "territory_id": territory_id,
        "checksum_sha256": checksum,
        "boundary_external_id": "la-galway-city",
        "boundary_name": "Galway City",
    }
    assert client.get("/api/v1/geography/territory-links").json() == [
        response.json()
    ]
    assert (tmp_path / "territory-boundary-links.json").exists()


def test_replaces_existing_link_for_same_territory(
    client: TestClient,
    tmp_path: Path,
) -> None:
    checksum = _stored_checksum(tmp_path)
    territory_id = _territory_id(client)
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    for boundary_external_id in ("la-galway-city", "la-cork-city"):
        response = client.put(
            f"/api/v1/geography/territory-links/{territory_id}",
            json={
                "checksum_sha256": checksum,
                "boundary_external_id": boundary_external_id,
            },
        )
        assert response.status_code == 200

    links = client.get("/api/v1/geography/territory-links").json()
    assert len(links) == 1
    assert links[0]["boundary_external_id"] == "la-cork-city"
    assert links[0]["boundary_name"] == "Cork City"


def test_rejects_missing_territory(client: TestClient, tmp_path: Path) -> None:
    checksum = _stored_checksum(tmp_path)
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.put(
        "/api/v1/geography/territory-links/missing-territory",
        json={
            "checksum_sha256": checksum,
            "boundary_external_id": "la-galway-city",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Territory not found."


def test_rejects_boundary_not_present_in_artifact(
    client: TestClient,
    tmp_path: Path,
) -> None:
    checksum = _stored_checksum(tmp_path)
    territory_id = _territory_id(client)
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.put(
        f"/api/v1/geography/territory-links/{territory_id}",
        json={
            "checksum_sha256": checksum,
            "boundary_external_id": "la-not-present",
        },
    )

    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]


def test_fails_closed_for_corrupt_link_store(
    client: TestClient,
    tmp_path: Path,
) -> None:
    (tmp_path / "territory-boundary-links.json").write_text(
        "not-json",
        encoding="utf-8",
    )
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/territory-links")

    assert response.status_code == 422
    assert "unreadable" in response.json()["detail"]
