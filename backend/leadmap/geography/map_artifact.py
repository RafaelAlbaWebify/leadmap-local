from copy import deepcopy
from math import hypot
from typing import Any

from .validation import BoundaryValidationError

MAP_SIMPLIFICATION_TOLERANCE = 0.0015


def _coordinate(value: object) -> tuple[float, float] | None:
    if not isinstance(value, list | tuple) or len(value) < 2:
        return None
    x, y = value[0], value[1]
    if not isinstance(x, int | float) or not isinstance(y, int | float):
        return None
    return float(x), float(y)


def simplify_ring(
    ring: object,
    *,
    tolerance: float = MAP_SIMPLIFICATION_TOLERANCE,
) -> list[list[float]]:
    if not isinstance(ring, list) or len(ring) < 4:
        raise BoundaryValidationError("Geographic ring must contain at least four coordinates.")

    coordinates = [_coordinate(value) for value in ring]
    if any(value is None for value in coordinates):
        raise BoundaryValidationError("Geographic ring contains an invalid coordinate.")
    points = [value for value in coordinates if value is not None]
    if points[0] != points[-1]:
        raise BoundaryValidationError("Geographic ring must be closed.")

    original = [[x, y] for x, y in points]
    unique_points = points[:-1]
    if len(unique_points) < 3:
        return original

    kept = [unique_points[0]]
    for point in unique_points[1:]:
        if hypot(point[0] - kept[-1][0], point[1] - kept[-1][1]) >= tolerance:
            kept.append(point)

    if kept[-1] != unique_points[-1]:
        kept.append(unique_points[-1])

    distinct = list(dict.fromkeys(kept))
    if len(distinct) < 3:
        return original

    simplified = [[x, y] for x, y in kept]
    simplified.append(simplified[0].copy())
    return simplified if len(simplified) >= 4 else original


def _simplify_polygon(coordinates: object) -> list[list[list[float]]]:
    if not isinstance(coordinates, list):
        raise BoundaryValidationError("Polygon coordinates are invalid.")
    return [simplify_ring(ring) for ring in coordinates]


def _simplify_multipolygon(coordinates: object) -> list[list[list[list[float]]]]:
    if not isinstance(coordinates, list):
        raise BoundaryValidationError("MultiPolygon coordinates are invalid.")
    return [_simplify_polygon(polygon) for polygon in coordinates]


def derive_map_artifact(document: dict[str, Any]) -> dict[str, Any]:
    boundaries = document.get("boundaries")
    if not isinstance(boundaries, list):
        raise BoundaryValidationError("Geographic artifact boundaries are invalid.")

    result = deepcopy(document)
    simplified_boundaries: list[dict[str, Any]] = []
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            raise BoundaryValidationError("Geographic artifact boundary is invalid.")
        simplified = deepcopy(boundary)
        geometry_type = boundary.get("geometry_type")
        if geometry_type == "Polygon":
            simplified["coordinates"] = _simplify_polygon(boundary.get("coordinates"))
        elif geometry_type == "MultiPolygon":
            simplified["coordinates"] = _simplify_multipolygon(boundary.get("coordinates"))
        else:
            raise BoundaryValidationError("Geographic artifact geometry type is unsupported.")
        simplified_boundaries.append(simplified)

    result["boundaries"] = simplified_boundaries
    return result
