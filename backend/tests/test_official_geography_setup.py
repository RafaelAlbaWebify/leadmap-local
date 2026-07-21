import json
from pathlib import Path

import pytest

from backend.leadmap.geography.official_setup import setup_official_geography
from backend.leadmap.geography.validation import BoundaryValidationError


def _source_bytes(*, authority_count: int = 31, invalid_geometry: bool = False) -> bytes:
    features = []
    for authority_index in range(authority_count):
        for fragment_index in range(2):
            longitude = -10.0 + authority_index * 0.1 + fragment_index * 0.01
            geometry_type = "Point" if invalid_geometry else "Polygon"
            coordinates: object
            if invalid_geometry:
                coordinates = [longitude, 52.0]
            else:
                coordinates = [
                    [
                        [longitude, 52.0],
                        [longitude + 0.005, 52.0],
                        [longitude + 0.005, 52.005],
                        [longitude, 52.005],
                        [longitude, 52.0],
                    ]
                ]
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "OBJECTID": authority_index * 2 + fragment_index + 1,
                        "ENG_NAME_VALUE": f"Authority {authority_index + 1}",
                    },
                    "geometry": {
                        "type": geometry_type,
                        "coordinates": coordinates,
                    },
                }
            )
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


def test_groups_fragments_and_reuses_artifact(tmp_path: Path) -> None:
    first = setup_official_geography(
        artifact_directory=tmp_path,
        source_bytes=_source_bytes(),
    )
    assert first["created"] is True
    assert first["feature_count"] == 31
    assert first["id_field"] == "LEADMAP_BOUNDARY_ID"
    assert first["name_field"] == "LEADMAP_BOUNDARY_NAME"
    artifact_path = Path(str(first["artifact_path"]))
    assert artifact_path.is_file()

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert len(artifact["boundaries"]) == 31
    assert all(
        boundary["geometry_type"] == "MultiPolygon"
        for boundary in artifact["boundaries"]
    )
    assert all(
        len(boundary["coordinates"]) == 2
        for boundary in artifact["boundaries"]
    )

    second = setup_official_geography(
        artifact_directory=tmp_path,
        source_bytes=_source_bytes(),
    )
    assert second["created"] is False
    assert second["checksum_sha256"] == first["checksum_sha256"]


def test_requires_exactly_31_grouped_authorities(tmp_path: Path) -> None:
    with pytest.raises(BoundaryValidationError, match="group into 31 authorities"):
        setup_official_geography(
            artifact_directory=tmp_path,
            source_bytes=_source_bytes(authority_count=30),
        )


def test_rejects_unsupported_fragment_geometry(tmp_path: Path) -> None:
    with pytest.raises(BoundaryValidationError, match="Polygon or MultiPolygon"):
        setup_official_geography(
            artifact_directory=tmp_path,
            source_bytes=_source_bytes(invalid_geometry=True),
        )
