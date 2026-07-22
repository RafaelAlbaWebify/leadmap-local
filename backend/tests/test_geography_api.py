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


def test_returns_validated_artifact_contract(client: TestClient, tmp_path: Path) -> None:
    checksum = _stored_checksum(tmp_path)
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get(f"/api/v1/geography/artifacts/{checksum}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["checksum_sha256"] == checksum
    assert payload["source"]["publisher"] == "Tailte Éireann"
    assert payload["feature_count"] == 2
    assert payload["boundaries"][0]["geometry_type"] in {"Polygon", "MultiPolygon"}


def test_compresses_geography_artifact_for_gzip_clients(
    client: TestClient,
    tmp_path: Path,
) -> None:
    checksum = _stored_checksum(tmp_path)
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get(
        f"/api/v1/geography/artifacts/{checksum}",
        headers={"Accept-Encoding": "gzip"},
    )

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert "Accept-Encoding" in response.headers["vary"]
    assert response.json()["checksum_sha256"] == checksum


def test_returns_not_found_for_missing_artifact(client: TestClient, tmp_path: Path) -> None:
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get(f"/api/v1/geography/artifacts/{'0' * 64}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Geographic artifact not found."


def test_rejects_invalid_checksum(client: TestClient, tmp_path: Path) -> None:
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/artifacts/not-a-checksum")

    assert response.status_code == 422
    assert "64 lowercase hex characters" in response.json()["detail"]


def test_rejects_corrupt_artifact(client: TestClient, tmp_path: Path) -> None:
    checksum = "a" * 64
    (tmp_path / f"boundaries-{checksum}.json").write_text("not-json", encoding="utf-8")
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get(f"/api/v1/geography/artifacts/{checksum}")

    assert response.status_code == 422
    assert "unreadable" in response.json()["detail"]
