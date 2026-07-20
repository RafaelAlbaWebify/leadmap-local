from dataclasses import dataclass
from typing import Literal

Coordinate = tuple[float, float]
LinearRing = tuple[Coordinate, ...]
PolygonCoordinates = tuple[LinearRing, ...]
MultiPolygonCoordinates = tuple[PolygonCoordinates, ...]
GeometryType = Literal["Polygon", "MultiPolygon"]
GeometryCoordinates = PolygonCoordinates | MultiPolygonCoordinates


@dataclass(frozen=True, slots=True)
class BoundingBox:
    west: float
    south: float
    east: float
    north: float


@dataclass(frozen=True, slots=True)
class NormalizedBoundary:
    external_id: str
    name: str
    geometry_type: GeometryType
    coordinates: GeometryCoordinates
    bounding_box: BoundingBox


@dataclass(frozen=True, slots=True)
class BoundaryCollection:
    boundaries: tuple[NormalizedBoundary, ...]
    feature_count: int
