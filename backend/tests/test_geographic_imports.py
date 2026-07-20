from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.leadmap.geography import (
    BoundarySourceMetadata,
    BoundaryValidationError,
    import_boundary_bytes,
)

FIXTURE = Path(__file__).parent / "fixtures" / "ireland_boundaries_sample.geojson"


def _source() -> BoundarySourceMetadata:
    return BoundarySourceMetadata(
        dataset_title="Local Authorities - National Statutory Boundaries - Ungeneralised 2026",
        publisher="Tailte Éireann",
        licence="CC BY 4.0",
        edition_year=2026,
        source_url="https://example.invalid/ireland-local-authorities.geojson",
        retrieved_at=datetime(2026, 7, 20, 10, 0, tzinfo=UTC),
    )


def test_import_records_provenance_checksum_and_feature_count() -> None:
    raw_data = FIXTURE.read_bytes()

    artifact = import_boundary_bytes(
        raw_data,
        source=_source(),
        id_field="boundary_id",
        name_field="name",
        expected_feature_count=2,
    )

    assert artifact.source.publisher == "Tailte Éireann"
    assert artifact.source.edition_year == 2026
    assert artifact.collection.feature_count == 2
    assert len(artifact.checksum_sha256) == 64
    assert artifact.idempotency_key == f"1:{artifact.checksum_sha256}"


def test_identical_source_bytes_produce_same_idempotency_key() -> None:
    raw_data = FIXTURE.read_bytes()

    first = import_boundary_bytes(
        raw_data,
        source=_source(),
        id_field="boundary_id",
        name_field="name",
    )
    second = import_boundary_bytes(
        raw_data,
        source=_source(),
        id_field="boundary_id",
        name_field="name",
    )

    assert first.idempotency_key == second.idempotency_key


def test_changed_source_bytes_produce_different_idempotency_key() -> None:
    raw_data = FIXTURE.read_bytes()
    changed_data = raw_data.replace(b"Galway City", b"Galway Urban Area")

    first = import_boundary_bytes(
        raw_data,
        source=_source(),
        id_field="boundary_id",
        name_field="name",
    )
    second = import_boundary_bytes(
        changed_data,
        source=_source(),
        id_field="boundary_id",
        name_field="name",
    )

    assert first.idempotency_key != second.idempotency_key


@pytest.mark.parametrize(
    ("raw_data", "message"),
    [
        (b"", "empty"),
        (b"\xff", "UTF-8"),
        (b'{"type":', "not valid JSON"),
    ],
)
def test_rejects_unreadable_sources(raw_data: bytes, message: str) -> None:
    with pytest.raises(BoundaryValidationError, match=message):
        import_boundary_bytes(
            raw_data,
            source=_source(),
            id_field="boundary_id",
            name_field="name",
        )
