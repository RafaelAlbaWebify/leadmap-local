import json
from copy import deepcopy
from pathlib import Path

import pytest

from backend.leadmap.market_indicators import (
    MarketIndicatorValidationError,
    install_market_indicator_artifact,
    list_market_indicator_artifacts,
    load_market_indicator_artifact,
    territory_indicator_values,
    validate_market_indicator_artifact,
)


def artifact() -> dict[str, object]:
    return {
        "schema_version": "1",
        "source": {
            "dataset_title": "Approved local business indicator fixture",
            "publisher": "Official Publisher",
            "source_url": "https://example.invalid/dataset",
            "licence": "CC BY 4.0",
            "published_at": "2026-01-15",
            "retrieved_at": "2026-07-27T12:00:00Z",
        },
        "records": [
            {
                "territory_key": "galway-city",
                "sector_key": "all",
                "indicator_key": "active-enterprises",
                "unit": "businesses",
                "value": 1250,
                "notes": "Fixture only.",
            },
            {
                "territory_key": "galway-city",
                "sector_key": "legal-services",
                "indicator_key": "sector-enterprises",
                "unit": "businesses",
                "value": 87,
            },
            {
                "territory_key": "dublin-city",
                "sector_key": "all",
                "indicator_key": "active-enterprises",
                "unit": "businesses",
                "value": 9200,
            },
        ],
    }


def test_validation_adds_stable_checksum_without_mutating_source() -> None:
    source = artifact()
    original = deepcopy(source)
    first = validate_market_indicator_artifact(source)
    second = validate_market_indicator_artifact(source)
    assert source == original
    assert first["checksum_sha256"] == second["checksum_sha256"]
    assert len(str(first["checksum_sha256"])) == 64


def test_install_load_and_catalog_are_checksum_addressed(tmp_path: Path) -> None:
    installed = install_market_indicator_artifact(artifact(), tmp_path)
    checksum = str(installed["checksum_sha256"])
    loaded = load_market_indicator_artifact(tmp_path, checksum)
    assert loaded == installed
    assert list_market_indicator_artifacts(tmp_path) == [
        {
            "schema_version": "1",
            "checksum_sha256": checksum,
            "source": installed["source"],
            "record_count": 3,
        }
    ]


def test_reinstall_is_idempotent(tmp_path: Path) -> None:
    first = install_market_indicator_artifact(artifact(), tmp_path)
    second = install_market_indicator_artifact(artifact(), tmp_path)
    assert first == second
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_territory_values_are_explicit_and_deterministic() -> None:
    document = validate_market_indicator_artifact(artifact())
    values = territory_indicator_values(document, "galway-city", "legal-services")
    assert [item["indicator_key"] for item in values] == ["active-enterprises", "sector-enterprises"]
    assert territory_indicator_values(document, "missing", None) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(schema_version="2"),
        lambda value: value.update(records=[]),
        lambda value: value["records"].append(dict(value["records"][0])),
        lambda value: value["records"][0].update(value=float("nan")),
        lambda value: value["source"].update(publisher=""),
    ],
)
def test_invalid_artifacts_fail_closed(mutate) -> None:
    value = artifact()
    mutate(value)
    with pytest.raises(MarketIndicatorValidationError):
        validate_market_indicator_artifact(value)


def test_tampered_installed_file_fails_checksum_validation(tmp_path: Path) -> None:
    installed = install_market_indicator_artifact(artifact(), tmp_path)
    checksum = str(installed["checksum_sha256"])
    path = tmp_path / f"{checksum}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["value"] = 9999
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MarketIndicatorValidationError):
        load_market_indicator_artifact(tmp_path, checksum)
