from copy import deepcopy

import pytest

from backend.leadmap.geography import (
    BoundaryValidationError,
    derive_map_artifact,
    simplify_ring,
)


def _document() -> dict[str, object]:
    ring = [[-10.0 + index * 0.0002, 53.0] for index in range(20)]
    ring.extend([[-9.9962, 53.01], [-10.0, 53.01], [-10.0, 53.0]])
    return {
        "schema_version": "1",
        "idempotency_key": "import-1",
        "checksum_sha256": "a" * 64,
        "source": {
            "dataset_title": "Authorities",
            "publisher": "Tailte Éireann",
            "licence": "CC BY 4.0",
            "edition_year": 2026,
            "source_url": "https://example.invalid/source",
            "retrieved_at": "2026-07-20T10:00:00+00:00",
        },
        "feature_count": 2,
        "boundaries": [
            {
                "external_id": "authority-1",
                "name": "Authority One",
                "geometry_type": "Polygon",
                "coordinates": [ring],
                "bounding_box": {
                    "west": -10.0,
                    "south": 53.0,
                    "east": -9.9962,
                    "north": 53.01,
                },
            },
            {
                "external_id": "authority-2",
                "name": "Authority Two",
                "geometry_type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [-9.0, 52.0],
                            [-8.9, 52.0],
                            [-8.9, 52.1],
                            [-9.0, 52.1],
                            [-9.0, 52.0],
                        ]
                    ]
                ],
                "bounding_box": {
                    "west": -9.0,
                    "south": 52.0,
                    "east": -8.9,
                    "north": 52.1,
                },
            },
        ],
    }


def test_map_artifact_reduces_points_and_preserves_identity() -> None:
    canonical = _document()
    original = deepcopy(canonical)

    mapped = derive_map_artifact(canonical)

    assert canonical == original
    assert mapped["checksum_sha256"] == canonical["checksum_sha256"]
    assert mapped["source"] == canonical["source"]
    assert mapped["feature_count"] == 2

    boundaries = mapped["boundaries"]
    assert isinstance(boundaries, list)
    assert [item["external_id"] for item in boundaries] == [
        "authority-1",
        "authority-2",
    ]
    simplified_ring = boundaries[0]["coordinates"][0]
    original_ring = original["boundaries"][0]["coordinates"][0]
    assert len(simplified_ring) < len(original_ring)
    assert simplified_ring[0] == simplified_ring[-1]
    assert len(simplified_ring) >= 4


def test_short_valid_ring_falls_back_to_original() -> None:
    ring = [[0.0, 0.0], [0.0001, 0.0], [0.0001, 0.0001], [0.0, 0.0]]
    assert simplify_ring(ring) == ring


@pytest.mark.parametrize(
    "ring",
    [
        [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0]],
        [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        [[0.0, 0.0], ["bad", 0.0], [1.0, 1.0], [0.0, 0.0]],
    ],
)
def test_invalid_ring_fails_closed(ring: list[object]) -> None:
    with pytest.raises(BoundaryValidationError):
        simplify_ring(ring)


def test_unsupported_geometry_fails_closed() -> None:
    document = _document()
    boundaries = document["boundaries"]
    assert isinstance(boundaries, list)
    boundaries[0]["geometry_type"] = "LineString"

    with pytest.raises(BoundaryValidationError, match="unsupported"):
        derive_map_artifact(document)
