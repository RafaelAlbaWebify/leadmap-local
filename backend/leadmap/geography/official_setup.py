import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .imports import BoundarySourceMetadata, import_boundary_bytes
from .storage import store_boundary_artifact
from .validation import BoundaryValidationError

SERVICE_URL = (
    "https://services-eu1.arcgis.com/FH5XCsx8rYXqnjF5/arcgis/rest/services/"
    "National_Statutory_Boundaries_-_Local_Authorities__Ungeneralised_-_2026/"
    "FeatureServer"
)
LAYER_ID = 3
OFFICIAL_GEOJSON_URL = f"{SERVICE_URL}/{LAYER_ID}"
DATASET_TITLE = "Local Authorities - National Statutory Boundaries - Ungeneralised 2026"
PUBLISHER = "Tailte Éireann"
LICENCE = "CC BY 4.0"
EDITION_YEAR = 2026
EXPECTED_FEATURE_COUNT = 31
EXPECTED_SOURCE_RECORDS = 9161
GROUP_FIELD = "ENG_NAME_VALUE"
OBJECT_ID_FIELD = "OBJECTID"
PAGE_SIZE = 2000
NORMALIZED_ID_FIELD = "LEADMAP_BOUNDARY_ID"
NORMALIZED_NAME_FIELD = "LEADMAP_BOUNDARY_NAME"


def _request_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "LeadMap-Local/0.3 geography setup"})
    try:
        with urlopen(request, timeout=240) as response:
            data = cast(bytes, response.read())
    except (OSError, URLError) as exc:
        raise BoundaryValidationError(f"Official GeoJSON download failed: {exc}") from exc
    if not data:
        raise BoundaryValidationError("Official GeoJSON download returned an empty response.")
    return data


def _page_url(offset: int) -> str:
    return f"{OFFICIAL_GEOJSON_URL}/query?" + urlencode(
        {
            "where": "1=1",
            "outFields": f"{OBJECT_ID_FIELD},{GROUP_FIELD}",
            "returnGeometry": "true",
            "outSR": "4326",
            "orderByFields": f"{OBJECT_ID_FIELD} ASC",
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
            "f": "geojson",
        }
    )


def _download_source_collection() -> dict[str, object]:
    features: list[object] = []
    offset = 0
    while True:
        try:
            page: object = json.loads(_request_bytes(_page_url(offset)).decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BoundaryValidationError("Official source is not valid UTF-8 JSON.") from exc
        if not isinstance(page, dict) or page.get("type") != "FeatureCollection":
            raise BoundaryValidationError(
                "Official source page is not a GeoJSON FeatureCollection."
            )
        page_features = page.get("features")
        if not isinstance(page_features, list):
            raise BoundaryValidationError("Official source page has an invalid feature array.")
        features.extend(page_features)
        if len(page_features) < PAGE_SIZE:
            break
        offset += len(page_features)
    if len(features) != EXPECTED_SOURCE_RECORDS:
        raise BoundaryValidationError(
            f"Official source must contain {EXPECTED_SOURCE_RECORDS} fragments; "
            f"found {len(features)}."
        )
    return {"type": "FeatureCollection", "features": features}


def _group_fragments(document: object) -> dict[str, object]:
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise BoundaryValidationError("Official source is not a GeoJSON FeatureCollection.")
    features = document.get("features")
    if not isinstance(features, list):
        raise BoundaryValidationError("Official source has an invalid feature array.")

    grouped: dict[str, list[object]] = defaultdict(list)
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise BoundaryValidationError(f"Feature {index} is invalid.")
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            raise BoundaryValidationError(f"Feature {index} is missing properties or geometry.")
        authority = properties.get(GROUP_FIELD)
        if not isinstance(authority, str) or not authority.strip():
            raise BoundaryValidationError(f"Feature {index} has no usable {GROUP_FIELD} value.")
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list):
            raise BoundaryValidationError(f"Feature {index} has invalid coordinates.")
        geometry_type = geometry.get("type")
        if geometry_type == "Polygon":
            grouped[authority.strip()].append(coordinates)
        elif geometry_type == "MultiPolygon":
            grouped[authority.strip()].extend(coordinates)
        else:
            raise BoundaryValidationError(
                f"Feature {index} geometry must be Polygon or MultiPolygon."
            )

    if len(grouped) != EXPECTED_FEATURE_COUNT:
        raise BoundaryValidationError(
            f"Official source must group into {EXPECTED_FEATURE_COUNT} authorities; "
            f"found {len(grouped)}."
        )

    normalized_features: list[dict[str, object]] = []
    for authority in sorted(grouped):
        normalized_features.append(
            {
                "type": "Feature",
                "properties": {
                    NORMALIZED_ID_FIELD: authority,
                    NORMALIZED_NAME_FIELD: authority,
                },
                "geometry": {"type": "MultiPolygon", "coordinates": grouped[authority]},
            }
        )
    return {"type": "FeatureCollection", "features": normalized_features}


def setup_official_geography(
    *,
    artifact_directory: Path,
    source_bytes: bytes | None = None,
) -> dict[str, object]:
    if source_bytes is None:
        source_document: object = _download_source_collection()
    else:
        try:
            source_document = json.loads(source_bytes.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BoundaryValidationError("Official source is not valid UTF-8 JSON.") from exc

    normalized_document = _group_fragments(source_document)
    normalized_bytes = json.dumps(
        normalized_document, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    retrieved_at = datetime.now(UTC)
    artifact = import_boundary_bytes(
        normalized_bytes,
        source=BoundarySourceMetadata(
            dataset_title=DATASET_TITLE,
            publisher=PUBLISHER,
            licence=LICENCE,
            edition_year=EDITION_YEAR,
            source_url=OFFICIAL_GEOJSON_URL,
            retrieved_at=retrieved_at,
        ),
        id_field=NORMALIZED_ID_FIELD,
        name_field=NORMALIZED_NAME_FIELD,
        expected_feature_count=EXPECTED_FEATURE_COUNT,
    )
    stored = store_boundary_artifact(artifact, directory=artifact_directory)
    return {
        "artifact_path": str(stored.path),
        "checksum_sha256": artifact.checksum_sha256,
        "created": stored.created,
        "feature_count": artifact.collection.feature_count,
        "id_field": NORMALIZED_ID_FIELD,
        "name_field": NORMALIZED_NAME_FIELD,
        "source_url": OFFICIAL_GEOJSON_URL,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadmap-setup-ireland-geography",
        description=(
            "Download, group, validate, and store the official 2026 Ireland "
            "local-authority boundaries."
        ),
    )
    parser.add_argument("--artifact-directory", type=Path, default=Path("data/geography"))
    return parser


def run_setup(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact_directory = cast(Path, args.artifact_directory)
    try:
        result = setup_official_geography(artifact_directory=artifact_directory)
    except BoundaryValidationError as exc:
        print(f"Official geography setup failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run_setup())


if __name__ == "__main__":
    main()
