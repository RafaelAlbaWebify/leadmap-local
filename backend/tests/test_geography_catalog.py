import json
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


def _store(directory: Path, *, retrieved_at: datetime, source_url: str) -> str:
    source_bytes = FIXTURE.read_bytes() + b"\n" + (b" " * retrieved_at.hour)
    artifact = import_boundary_bytes(
        source_bytes,
        source=BoundarySourceMetadata(
            dataset_title="Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
            publisher="Tailte Éireann",
            licence="CC BY 4.0",
            edition_year=2026,
            source_url=source_url,
            retrieved_at=retrieved_at,
        ),
        id_field="boundary_id",
        name_field="name",
        expected_feature_count=2,
    )
    store_boundary_artifact(artifact, directory=directory)
    return artifact.checksum_sha256


def test_catalog_returns_empty_list_when_directory_is_missing(
    client: TestClient, tmp_path: Path
) -> None:
    missing = tmp_path / "missing"
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: missing

    response = client.get("/api/v1/geography/artifacts")

    assert response.status_code == 200
    assert response.json() == []


def test_catalog_returns_validated_summaries_newest_first(
    client: TestClient, tmp_path: Path
) -> None:
    older_checksum = _store(
        tmp_path,
        retrieved_at=datetime(2026, 7, 20, 9, 0, tzinfo=UTC),
        source_url="https://example.invalid/older.geojson",
    )
    newer_checksum = _store(
        tmp_path,
        retrieved_at=datetime(2026, 7, 20, 11, 0, tzinfo=UTC),
        source_url="https://example.invalid/newer.geojson",
    )
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/artifacts")

    assert response.status_code == 200
    payload = response.json()
    assert [item["checksum_sha256"] for item in payload] == [newer_checksum, older_checksum]
    assert payload[0]["feature_count"] == 2
    assert payload[0]["source"]["publisher"] == "Tailte Éireann"
    assert "boundaries" not in payload[0]


def test_catalog_ignores_unrelated_files(client: TestClient, tmp_path: Path) -> None:
    checksum = _store(
        tmp_path,
        retrieved_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
        source_url="https://example.invalid/boundaries.geojson",
    )
    (tmp_path / "notes.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".temporary.tmp").write_text("ignored", encoding="utf-8")
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/artifacts")

    assert response.status_code == 200
    assert [item["checksum_sha256"] for item in response.json()] == [checksum]


def test_catalog_rejects_corrupt_matching_artifact(client: TestClient, tmp_path: Path) -> None:
    checksum = "b" * 64
    path = tmp_path / f"boundaries-{checksum}.json"
    path.write_text(json.dumps({"checksum_sha256": checksum}), encoding="utf-8")
    app.dependency_overrides[get_geographic_artifact_directory] = lambda: tmp_path

    response = client.get("/api/v1/geography/artifacts")

    assert response.status_code == 422
    assert "schema is unsupported" in response.json()["detail"]
