from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any


class MarketIndicatorValidationError(ValueError):
    pass


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MarketIndicatorValidationError(f"{field} must be non-empty text.")
    return value.strip()


def _canonical_payload(document: dict[str, object]) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "checksum_sha256"
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def validate_market_indicator_artifact(document: object) -> dict[str, object]:
    if not isinstance(document, dict):
        raise MarketIndicatorValidationError("Artifact must be a JSON object.")
    result = deepcopy(document)
    if result.get("schema_version") != "1":
        raise MarketIndicatorValidationError(
            "Unsupported market indicator schema version."
        )

    source = result.get("source")
    if not isinstance(source, dict):
        raise MarketIndicatorValidationError("source must be an object.")
    fields = (
        "dataset_title",
        "publisher",
        "source_url",
        "licence",
        "published_at",
        "retrieved_at",
    )
    for field in fields:
        source[field] = _required_text(source.get(field), f"source.{field}")

    records = result.get("records")
    if not isinstance(records, list) or not records:
        raise MarketIndicatorValidationError(
            "records must contain at least one item."
        )

    identities: set[tuple[str, str, str]] = set()
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise MarketIndicatorValidationError(
                f"records[{index}] must be an object."
            )
        record = dict(item)
        territory_key = _required_text(
            record.get("territory_key"),
            f"records[{index}].territory_key",
        )
        indicator_key = _required_text(
            record.get("indicator_key"),
            f"records[{index}].indicator_key",
        )
        sector_key = _required_text(
            record.get("sector_key", "all"),
            f"records[{index}].sector_key",
        )
        unit = _required_text(
            record.get("unit"),
            f"records[{index}].unit",
        )
        value = record.get("value")
        is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
        if not is_number or not math.isfinite(float(value)):
            raise MarketIndicatorValidationError(
                f"records[{index}].value must be finite numeric data."
            )
        identity = (territory_key, sector_key, indicator_key)
        if identity in identities:
            raise MarketIndicatorValidationError(
                "Duplicate territory, sector and indicator identity."
            )
        identities.add(identity)
        notes = record.get("notes")
        normalized.append(
            {
                "territory_key": territory_key,
                "sector_key": sector_key,
                "indicator_key": indicator_key,
                "unit": unit,
                "value": value,
                "notes": notes if isinstance(notes, str) else None,
            }
        )
    result["records"] = normalized

    expected = hashlib.sha256(_canonical_payload(result)).hexdigest()
    checksum = result.get("checksum_sha256")
    if checksum is not None and checksum != expected:
        raise MarketIndicatorValidationError(
            "checksum_sha256 does not match the canonical artifact payload."
        )
    result["checksum_sha256"] = expected
    return result


def install_market_indicator_artifact(
    document: object,
    directory: Path,
) -> dict[str, object]:
    validated = validate_market_indicator_artifact(document)
    directory.mkdir(parents=True, exist_ok=True)
    checksum = str(validated["checksum_sha256"])
    target = directory / f"{checksum}.json"
    encoded = (
        json.dumps(validated, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    )
    if target.exists():
        stored = json.loads(target.read_text(encoding="utf-8"))
        existing = validate_market_indicator_artifact(stored)
        if existing != validated:
            raise MarketIndicatorValidationError(
                "Installed checksum points to different content."
            )
        return existing
    target.write_text(encoded, encoding="utf-8")
    return validated


def load_market_indicator_artifact(
    directory: Path,
    checksum_sha256: str,
) -> dict[str, object]:
    valid_chars = set("0123456789abcdef")
    valid_checksum = len(checksum_sha256) == 64 and set(checksum_sha256) <= valid_chars
    if not valid_checksum:
        raise MarketIndicatorValidationError("Invalid checksum format.")
    path = directory / f"{checksum_sha256}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    validated = validate_market_indicator_artifact(document)
    if validated["checksum_sha256"] != checksum_sha256:
        raise MarketIndicatorValidationError(
            "Artifact filename and checksum differ."
        )
    return validated


def list_market_indicator_artifacts(
    directory: Path,
) -> list[dict[str, object]]:
    if not directory.exists():
        return []
    summaries: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.json")):
        document = load_market_indicator_artifact(directory, path.stem)
        records = document["records"]
        assert isinstance(records, list)
        summaries.append(
            {
                "schema_version": document["schema_version"],
                "checksum_sha256": document["checksum_sha256"],
                "source": document["source"],
                "record_count": len(records),
            }
        )
    return summaries


def territory_indicator_values(
    document: dict[str, object],
    territory_key: str,
    sector_key: str | None = None,
) -> list[dict[str, object]]:
    records = document.get("records")
    if not isinstance(records, list):
        raise MarketIndicatorValidationError("Artifact records are invalid.")
    selected = [
        dict(item)
        for item in records
        if isinstance(item, dict)
        and item.get("territory_key") == territory_key
        and (sector_key is None or item.get("sector_key") in {"all", sector_key})
    ]
    return sorted(
        selected,
        key=lambda item: (
            str(item["indicator_key"]),
            str(item["sector_key"]),
        ),
    )
