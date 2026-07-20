import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.leadmap.geography import (
    ARTIFACT_SCHEMA_VERSION,
    BoundaryImportArtifact,
    BoundarySourceMetadata,
    BoundaryValidationError,
    import_boundary_bytes,
    store_boundary_artifact,
)

FIXTURE = Path(__file__).parent / "fixtures" / "ireland_boundaries_sample.geojson"


def _artifact(retrieved_at: datetime) -> BoundaryImportArtifact:
    return import_boundary_bytes(
        FIXTURE.read_bytes(),
        source=BoundarySourceMetadata(
            dataset_title="Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
            publisher="Tailte Éireann",
            licence="CC BY 4.0",
            edition_year=2026,
            source_url="https://example.invalid/ireland-local-authorities.geojson",
            retrieved_at=retrieved_at,
        ),
        id_field="boundary_id",
        name_field="name",
        expected_feature_count=2,
    )


def test_stores_normalized_artifact_with_provenance(tmp_path: Path) -> None:
    artifact = _artifact(datetime(2026, 7, 20, 10, 0, tzinfo=UTC))

    stored = store_boundary_artifact(artifact, directory=tmp_path)

    assert stored.created is True
    assert stored.path.exists()
    document = json.loads(stored.path.read_text(encoding="utf-8"))
    assert document["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert document["checksum_sha256"] == artifact.checksum_sha256
    assert document["source"]["publisher"] == "Tailte Éireann"
    assert document["feature_count"] == 2
    assert document["boundaries"][0]["bounding_box"]["west"] == -9.2


def test_repeated_identical_import_does_not_overwrite_artifact(tmp_path: Path) -> None:
    first_artifact = _artifact(datetime(2026, 7, 20, 10, 0, tzinfo=UTC))
    second_artifact = _artifact(datetime(2026, 7, 20, 11, 0, tzinfo=UTC))

    first = store_boundary_artifact(first_artifact, directory=tmp_path)
    original_bytes = first.path.read_bytes()
    second = store_boundary_artifact(second_artifact, directory=tmp_path)

    assert first.created is True
    assert second.created is False
    assert second.path == first.path
    assert second.path.read_bytes() == original_bytes


def test_rejects_corrupt_existing_artifact(tmp_path: Path) -> None:
    artifact = _artifact(datetime(2026, 7, 20, 10, 0, tzinfo=UTC))
    target = tmp_path / f"boundaries-{artifact.checksum_sha256}.json"
    target.write_text("not-json", encoding="utf-8")

    with pytest.raises(BoundaryValidationError, match="unreadable"):
        store_boundary_artifact(artifact, directory=tmp_path)


def test_atomic_write_leaves_no_temporary_files(tmp_path: Path) -> None:
    artifact = _artifact(datetime(2026, 7, 20, 10, 0, tzinfo=UTC))

    store_boundary_artifact(artifact, directory=tmp_path)

    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob(".*.tmp")) == []
