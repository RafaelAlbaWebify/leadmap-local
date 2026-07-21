import json
from pathlib import Path

import pytest

from backend.leadmap.geography.official_setup import setup_official_geography
from backend.leadmap.geography.validation import BoundaryValidationError


def _source_bytes(*, include_known_fields: bool = True) -> bytes:
    features = []
    for index in range(31):
        properties: dict[str, object]
        if include_known_fields:
            properties = {
                "LA_CODE": f"LA-{index + 1}",
                "LOCAL_AUTHORITY": f"Authority {index + 1}",
            }
        else:
            properties = {
                "unknown_code": index + 1,
                "unknown_label": f"Authority {index + 1}",
            }
        longitude = -10.0 + index * 0.01
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [longitude, 52.0],
                            [longitude + 0.005, 52.0],
                            [longitude + 0.005, 52.005],
                            [longitude, 52.005],
                            [longitude, 52.0],
                        ]
                    ],
                },
            }
        )
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


def test_sets_up_official_geography_and_reuses_artifact(tmp_path: Path) -> None:
    first = setup_official_geography(
        artifact_directory=tmp_path,
        source_bytes=_source_bytes(),
    )
    assert first["created"] is True
    assert first["feature_count"] == 31
    assert first["id_field"] == "LA_CODE"
    assert first["name_field"] == "LOCAL_AUTHORITY"
    assert Path(str(first["artifact_path"])).is_file()

    second = setup_official_geography(
        artifact_directory=tmp_path,
        source_bytes=_source_bytes(),
    )
    assert second["created"] is False
    assert second["checksum_sha256"] == first["checksum_sha256"]


def test_fails_closed_when_fields_cannot_be_identified(tmp_path: Path) -> None:
    with pytest.raises(BoundaryValidationError, match="Available fields"):
        setup_official_geography(
            artifact_directory=tmp_path,
            source_bytes=_source_bytes(include_known_fields=False),
        )


def test_requires_exactly_31_features(tmp_path: Path) -> None:
    document = json.loads(_source_bytes())
    document["features"].pop()

    with pytest.raises(BoundaryValidationError, match="must contain 31 features"):
        setup_official_geography(
            artifact_directory=tmp_path,
            source_bytes=json.dumps(document).encode(),
        )
