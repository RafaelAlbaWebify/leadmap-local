import json
from pathlib import Path

import pytest

from backend.leadmap.geography import BoundaryValidationError, validate_feature_collection

FIXTURE = Path(__file__).parent / "fixtures" / "ireland_boundaries_sample.geojson"


def _fixture_payload() -> object:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_validates_polygon_and_multipolygon_fixture() -> None:
    collection = validate_feature_collection(
        _fixture_payload(),
        id_field="boundary_id",
        name_field="name",
        expected_feature_count=2,
    )

    assert collection.feature_count == 2
    assert collection.boundaries[0].name == "Galway City"
    assert collection.boundaries[0].geometry_type == "Polygon"
    assert collection.boundaries[0].bounding_box.west == -9.2
    assert collection.boundaries[1].geometry_type == "MultiPolygon"
    assert collection.boundaries[1].bounding_box.east == -8.3


def test_rejects_duplicate_normalized_names() -> None:
    payload = _fixture_payload()
    assert isinstance(payload, dict)
    features = payload["features"]
    assert isinstance(features, list)
    duplicate = features[1]
    assert isinstance(duplicate, dict)
    properties = duplicate["properties"]
    assert isinstance(properties, dict)
    properties["name"] = "  GALWAY   CITY "

    with pytest.raises(BoundaryValidationError, match="Duplicate boundary name"):
        validate_feature_collection(payload, id_field="boundary_id", name_field="name")


def test_rejects_out_of_bounds_coordinates() -> None:
    payload = _fixture_payload()
    assert isinstance(payload, dict)
    features = payload["features"]
    assert isinstance(features, list)
    first = features[0]
    assert isinstance(first, dict)
    geometry = first["geometry"]
    assert isinstance(geometry, dict)
    coordinates = geometry["coordinates"]
    assert isinstance(coordinates, list)
    coordinates[0][0] = [181, 53.2]

    with pytest.raises(BoundaryValidationError, match="longitude"):
        validate_feature_collection(payload, id_field="boundary_id", name_field="name")


def test_rejects_unclosed_linear_ring() -> None:
    payload = _fixture_payload()
    assert isinstance(payload, dict)
    features = payload["features"]
    assert isinstance(features, list)
    first = features[0]
    assert isinstance(first, dict)
    geometry = first["geometry"]
    assert isinstance(geometry, dict)
    coordinates = geometry["coordinates"]
    assert isinstance(coordinates, list)
    coordinates[0][-1] = [-9.1, 53.2]

    with pytest.raises(BoundaryValidationError, match="must be closed"):
        validate_feature_collection(payload, id_field="boundary_id", name_field="name")


def test_rejects_unexpected_dataset_feature_count() -> None:
    with pytest.raises(BoundaryValidationError, match="supported dataset edition"):
        validate_feature_collection(
            _fixture_payload(),
            id_field="boundary_id",
            name_field="name",
            expected_feature_count=31,
        )
