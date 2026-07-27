from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

from .map_artifact import MAP_SIMPLIFICATION_TOLERANCE, derive_map_artifact
from .validation import BoundaryValidationError

Clock = Callable[[], float]


@dataclass(frozen=True)
class GeographyDiagnostics:
    checksum_sha256: str
    feature_count: int
    canonical_json_bytes: int
    map_json_bytes: int
    canonical_coordinate_count: int
    map_coordinate_count: int
    byte_reduction_percent: float
    coordinate_reduction_percent: float
    simplification_tolerance: float
    derivation_duration_ms: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _json_bytes(document: dict[str, Any]) -> int:
    payload = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return len(payload.encode("utf-8"))


def _ring_coordinate_count(ring: object) -> int:
    if not isinstance(ring, list) or len(ring) < 4:
        raise BoundaryValidationError("Geographic ring must contain at least four coordinates.")
    for coordinate in ring:
        if not isinstance(coordinate, list | tuple) or len(coordinate) < 2:
            raise BoundaryValidationError("Geographic ring contains an invalid coordinate.")
        x, y = coordinate[0], coordinate[1]
        if not isinstance(x, int | float) or not isinstance(y, int | float):
            raise BoundaryValidationError("Geographic ring contains an invalid coordinate.")
    if tuple(ring[0][:2]) != tuple(ring[-1][:2]):
        raise BoundaryValidationError("Geographic ring must be closed.")
    return len(ring)


def coordinate_count(document: dict[str, Any]) -> int:
    boundaries = document.get("boundaries")
    if not isinstance(boundaries, list):
        raise BoundaryValidationError("Geographic artifact boundaries are invalid.")

    total = 0
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            raise BoundaryValidationError("Geographic artifact boundary is invalid.")
        geometry_type = boundary.get("geometry_type")
        coordinates = boundary.get("coordinates")
        if geometry_type == "Polygon":
            if not isinstance(coordinates, list):
                raise BoundaryValidationError("Polygon coordinates are invalid.")
            total += sum(_ring_coordinate_count(ring) for ring in coordinates)
        elif geometry_type == "MultiPolygon":
            if not isinstance(coordinates, list):
                raise BoundaryValidationError("MultiPolygon coordinates are invalid.")
            for polygon in coordinates:
                if not isinstance(polygon, list):
                    raise BoundaryValidationError("MultiPolygon polygon coordinates are invalid.")
                total += sum(_ring_coordinate_count(ring) for ring in polygon)
        else:
            raise BoundaryValidationError("Geographic artifact geometry type is unsupported.")
    return total


def _reduction_percent(before: int, after: int) -> float:
    if before <= 0:
        return 0.0
    return round((before - after) * 100 / before, 3)


def build_geography_diagnostics(
    canonical: dict[str, Any],
    *,
    clock: Clock = perf_counter,
) -> GeographyDiagnostics:
    original = deepcopy(canonical)
    started = clock()
    mapped = derive_map_artifact(canonical)
    finished = clock()
    if canonical != original:
        raise BoundaryValidationError("Geographic diagnostics mutated the canonical artifact.")

    checksum = canonical.get("checksum_sha256")
    feature_count = canonical.get("feature_count")
    map_checksum = mapped.get("checksum_sha256")
    map_feature_count = mapped.get("feature_count")
    if not isinstance(checksum, str) or not checksum:
        raise BoundaryValidationError("Geographic artifact checksum is invalid.")
    if not isinstance(feature_count, int) or feature_count < 0:
        raise BoundaryValidationError("Geographic artifact feature count is invalid.")
    if map_checksum != checksum or map_feature_count != feature_count:
        raise BoundaryValidationError("Map artifact identity does not match the canonical artifact.")

    canonical_bytes = _json_bytes(canonical)
    map_bytes = _json_bytes(mapped)
    canonical_coordinates = coordinate_count(canonical)
    map_coordinates = coordinate_count(mapped)

    return GeographyDiagnostics(
        checksum_sha256=checksum,
        feature_count=feature_count,
        canonical_json_bytes=canonical_bytes,
        map_json_bytes=map_bytes,
        canonical_coordinate_count=canonical_coordinates,
        map_coordinate_count=map_coordinates,
        byte_reduction_percent=_reduction_percent(canonical_bytes, map_bytes),
        coordinate_reduction_percent=_reduction_percent(canonical_coordinates, map_coordinates),
        simplification_tolerance=MAP_SIMPLIFICATION_TOLERANCE,
        derivation_duration_ms=round(max(0.0, finished - started) * 1000, 3),
    )
