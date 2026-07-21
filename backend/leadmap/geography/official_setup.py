import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.error import URLError
from urllib.request import Request, urlopen

from .imports import BoundarySourceMetadata, import_boundary_bytes
from .storage import store_boundary_artifact
from .validation import BoundaryValidationError

OFFICIAL_GEOJSON_URL = (
    "https://data-osi.opendata.arcgis.com/api/download/v1/items/"
    "74b839e09e1c48f2b2fe4efccb52a73d/geojson?layers=3"
)
DATASET_TITLE = "Local Authorities - National Statutory Boundaries - Ungeneralised 2026"
PUBLISHER = "Tailte Éireann"
LICENCE = "CC BY 4.0"
EDITION_YEAR = 2026
EXPECTED_FEATURE_COUNT = 31

_ID_CANDIDATES = (
    "local_authority_id",
    "localauthorityid",
    "la_id",
    "la_code",
    "code",
    "objectid",
    "fid",
    "id",
)
_NAME_CANDIDATES = (
    "local_authority",
    "localauthority",
    "local_authority_name",
    "localauthorityname",
    "la_name",
    "name",
    "english_name",
)


def _normalise_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "LeadMap-Local/0.3 geography setup"})
    try:
        with urlopen(request, timeout=60) as response:
            data = cast(bytes, response.read())
    except (OSError, URLError) as exc:
        raise BoundaryValidationError(f"Official GeoJSON download failed: {exc}") from exc
    if not data:
        raise BoundaryValidationError("Official GeoJSON download returned an empty response.")
    return data


def _feature_properties(document: object) -> list[Mapping[str, Any]]:
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise BoundaryValidationError("Official source is not a GeoJSON FeatureCollection.")
    features = document.get("features")
    if not isinstance(features, list) or len(features) != EXPECTED_FEATURE_COUNT:
        actual = len(features) if isinstance(features, list) else "invalid"
        raise BoundaryValidationError(
            f"Official source must contain {EXPECTED_FEATURE_COUNT} features; found {actual}."
        )
    properties: list[Mapping[str, Any]] = []
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise BoundaryValidationError(f"Feature {index} has invalid properties.")
        feature_properties = feature.get("properties")
        if not isinstance(feature_properties, dict):
            raise BoundaryValidationError(f"Feature {index} has invalid properties.")
        properties.append(cast(Mapping[str, Any], feature_properties))
    return properties


def _choose_field(
    properties: Sequence[Mapping[str, Any]],
    *,
    candidates: Sequence[str],
    require_unique: bool,
) -> str:
    available = list(properties[0].keys())
    normalised = {_normalise_key(key): key for key in available}
    for candidate in candidates:
        key = normalised.get(_normalise_key(candidate))
        if key is None:
            continue
        values = [item.get(key) for item in properties]
        if any(value is None or str(value).strip() == "" for value in values):
            continue
        if require_unique and len({str(value).strip() for value in values}) != len(values):
            continue
        return key
    raise BoundaryValidationError(
        "Could not identify a safe property field. Available fields: " + ", ".join(available)
    )


def setup_official_geography(
    *,
    artifact_directory: Path,
    download_url: str = OFFICIAL_GEOJSON_URL,
    source_bytes: bytes | None = None,
) -> dict[str, object]:
    raw_data = source_bytes if source_bytes is not None else _download(download_url)
    try:
        document: object = json.loads(raw_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryValidationError("Official source is not valid UTF-8 JSON.") from exc

    properties = _feature_properties(document)
    id_field = _choose_field(properties, candidates=_ID_CANDIDATES, require_unique=True)
    name_field = _choose_field(properties, candidates=_NAME_CANDIDATES, require_unique=True)
    retrieved_at = datetime.now(UTC)
    artifact = import_boundary_bytes(
        raw_data,
        source=BoundarySourceMetadata(
            dataset_title=DATASET_TITLE,
            publisher=PUBLISHER,
            licence=LICENCE,
            edition_year=EDITION_YEAR,
            source_url=download_url,
            retrieved_at=retrieved_at,
        ),
        id_field=id_field,
        name_field=name_field,
        expected_feature_count=EXPECTED_FEATURE_COUNT,
    )
    stored = store_boundary_artifact(artifact, directory=artifact_directory)
    return {
        "artifact_path": str(stored.path),
        "checksum_sha256": artifact.checksum_sha256,
        "created": stored.created,
        "feature_count": artifact.collection.feature_count,
        "id_field": id_field,
        "name_field": name_field,
        "source_url": download_url,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadmap-setup-ireland-geography",
        description=(
            "Download, validate, and store the official 2026 Ireland local-authority boundaries."
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
