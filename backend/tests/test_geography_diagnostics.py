from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from backend.leadmap.geography.diagnostics import (
    build_geography_diagnostics,
    coordinate_count,
)
from backend.leadmap.geography.validation import BoundaryValidationError

FIXTURE = Path(__file__).parent / "fixtures" / "geography-diagnostics-artifact.json"


def _document() -> dict[str, object]:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_coordinate_count_covers_polygon_and_multipolygon() -> None:
    assert coordinate_count(_document()) == 19


def test_diagnostics_report_reduction_and_preserve_source() -> None:
    canonical = _document()
    original = deepcopy(canonical)
    ticks = iter([10.0, 10.125])

    diagnostics = build_geography_diagnostics(canonical, clock=lambda: next(ticks))

    assert canonical == original
    assert diagnostics.checksum_sha256 == "a" * 64
    assert diagnostics.feature_count == 2
    assert diagnostics.canonical_coordinate_count == 19
    assert diagnostics.map_coordinate_count < diagnostics.canonical_coordinate_count
    assert diagnostics.map_json_bytes < diagnostics.canonical_json_bytes
    assert diagnostics.byte_reduction_percent > 0
    assert diagnostics.coordinate_reduction_percent > 0
    assert diagnostics.derivation_duration_ms == 125.0
    assert diagnostics.simplification_tolerance == 0.0015


def test_diagnostics_non_timing_fields_are_deterministic() -> None:
    first_ticks = iter([1.0, 1.1])
    second_ticks = iter([4.0, 4.9])
    first = build_geography_diagnostics(_document(), clock=lambda: next(first_ticks)).to_dict()
    second = build_geography_diagnostics(_document(), clock=lambda: next(second_ticks)).to_dict()

    first.pop("derivation_duration_ms")
    second.pop("derivation_duration_ms")
    assert first == second


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document.update({"checksum_sha256": ""}),
        lambda document: document.update({"feature_count": -1}),
        lambda document: document["boundaries"][0].update({"geometry_type": "LineString"}),
        lambda document: document["boundaries"][0].update({"coordinates": [[[0.0, 0.0]]]}),
    ],
)
def test_invalid_artifacts_fail_closed(mutation: object) -> None:
    document = _document()
    assert callable(mutation)
    mutation(document)
    with pytest.raises(BoundaryValidationError):
        build_geography_diagnostics(document)
