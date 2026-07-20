import math
from collections.abc import Mapping, Sequence
from typing import cast

from .models import (
    BoundaryCollection,
    BoundingBox,
    Coordinate,
    GeometryCoordinates,
    GeometryType,
    LinearRing,
    MultiPolygonCoordinates,
    NormalizedBoundary,
    PolygonCoordinates,
)


class BoundaryValidationError(ValueError):
    pass


def _require_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise BoundaryValidationError(f"{path} must be an object.")
    return value


def _require_sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise BoundaryValidationError(f"{path} must be an array.")
    return value


def _require_text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BoundaryValidationError(f"{path} must be a non-empty string.")
    return value.strip()


def _normalize_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _parse_coordinate(value: object, path: str) -> Coordinate:
    sequence = _require_sequence(value, path)
    if len(sequence) < 2:
        raise BoundaryValidationError(f"{path} must contain longitude and latitude.")

    longitude = sequence[0]
    latitude = sequence[1]
    if isinstance(longitude, bool) or not isinstance(longitude, int | float):
        raise BoundaryValidationError(f"{path}[0] must be a finite number.")
    if isinstance(latitude, bool) or not isinstance(latitude, int | float):
        raise BoundaryValidationError(f"{path}[1] must be a finite number.")

    lon = float(longitude)
    lat = float(latitude)
    if not math.isfinite(lon) or not math.isfinite(lat):
        raise BoundaryValidationError(f"{path} coordinates must be finite.")
    if not -180 <= lon <= 180:
        raise BoundaryValidationError(f"{path} longitude must be between -180 and 180.")
    if not -90 <= lat <= 90:
        raise BoundaryValidationError(f"{path} latitude must be between -90 and 90.")
    return lon, lat


def _parse_ring(value: object, path: str) -> LinearRing:
    sequence = _require_sequence(value, path)
    coordinates = tuple(
        _parse_coordinate(item, f"{path}[{index}]") for index, item in enumerate(sequence)
    )
    if len(coordinates) < 4:
        raise BoundaryValidationError(f"{path} must contain at least four positions.")
    if coordinates[0] != coordinates[-1]:
        raise BoundaryValidationError(f"{path} must be closed.")
    return coordinates


def _parse_polygon(value: object, path: str) -> PolygonCoordinates:
    sequence = _require_sequence(value, path)
    if not sequence:
        raise BoundaryValidationError(f"{path} must contain at least one linear ring.")
    return tuple(_parse_ring(item, f"{path}[{index}]") for index, item in enumerate(sequence))


def _parse_multi_polygon(value: object, path: str) -> MultiPolygonCoordinates:
    sequence = _require_sequence(value, path)
    if not sequence:
        raise BoundaryValidationError(f"{path} must contain at least one polygon.")
    return tuple(_parse_polygon(item, f"{path}[{index}]") for index, item in enumerate(sequence))


def _polygon_points(polygon: PolygonCoordinates) -> tuple[Coordinate, ...]:
    return tuple(point for ring in polygon for point in ring)


def _all_coordinates(
    geometry_type: GeometryType, coordinates: GeometryCoordinates
) -> tuple[Coordinate, ...]:
    if geometry_type == "Polygon":
        return _polygon_points(cast(PolygonCoordinates, coordinates))

    multi_polygon = cast(MultiPolygonCoordinates, coordinates)
    return tuple(point for polygon in multi_polygon for point in _polygon_points(polygon))


def _bounding_box(geometry_type: GeometryType, coordinates: GeometryCoordinates) -> BoundingBox:
    points = _all_coordinates(geometry_type, coordinates)
    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]
    return BoundingBox(
        west=min(longitudes),
        south=min(latitudes),
        east=max(longitudes),
        north=max(latitudes),
    )


def validate_feature_collection(
    payload: object,
    *,
    id_field: str,
    name_field: str,
    expected_feature_count: int | None = None,
) -> BoundaryCollection:
    root = _require_mapping(payload, "root")
    if root.get("type") != "FeatureCollection":
        raise BoundaryValidationError("root.type must be 'FeatureCollection'.")

    features = _require_sequence(root.get("features"), "root.features")
    if expected_feature_count is not None and len(features) != expected_feature_count:
        raise BoundaryValidationError(
            "root.features count does not match the supported dataset edition: "
            f"expected {expected_feature_count}, received {len(features)}."
        )

    boundaries: list[NormalizedBoundary] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()

    for index, item in enumerate(features):
        feature_path = f"root.features[{index}]"
        feature = _require_mapping(item, feature_path)
        if feature.get("type") != "Feature":
            raise BoundaryValidationError(f"{feature_path}.type must be 'Feature'.")

        properties = _require_mapping(feature.get("properties"), f"{feature_path}.properties")
        external_id = _require_text(
            properties.get(id_field), f"{feature_path}.properties.{id_field}"
        )
        name = _require_text(properties.get(name_field), f"{feature_path}.properties.{name_field}")

        normalized_id = _normalize_key(external_id)
        normalized_name = _normalize_key(name)
        if normalized_id in seen_ids:
            raise BoundaryValidationError(f"Duplicate boundary identifier: {external_id!r}.")
        if normalized_name in seen_names:
            raise BoundaryValidationError(f"Duplicate boundary name: {name!r}.")

        geometry = _require_mapping(feature.get("geometry"), f"{feature_path}.geometry")
        geometry_type_value = geometry.get("type")
        if geometry_type_value == "Polygon":
            geometry_type: GeometryType = "Polygon"
            coordinates: GeometryCoordinates = _parse_polygon(
                geometry.get("coordinates"), f"{feature_path}.geometry.coordinates"
            )
        elif geometry_type_value == "MultiPolygon":
            geometry_type = "MultiPolygon"
            coordinates = _parse_multi_polygon(
                geometry.get("coordinates"), f"{feature_path}.geometry.coordinates"
            )
        else:
            raise BoundaryValidationError(
                f"{feature_path}.geometry.type must be 'Polygon' or 'MultiPolygon'."
            )

        seen_ids.add(normalized_id)
        seen_names.add(normalized_name)
        boundaries.append(
            NormalizedBoundary(
                external_id=external_id,
                name=name,
                geometry_type=geometry_type,
                coordinates=coordinates,
                bounding_box=_bounding_box(geometry_type, coordinates),
            )
        )

    return BoundaryCollection(boundaries=tuple(boundaries), feature_count=len(boundaries))
