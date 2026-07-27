from pathlib import Path

from fastapi.testclient import TestClient

from backend.leadmap.api.market_indicator_routes import get_market_indicator_directory
from backend.leadmap.main import app
from backend.leadmap.market_indicators import install_market_indicator_artifact


def artifact() -> dict[str, object]:
    return {
        "schema_version": "1",
        "source": {
            "dataset_title": "Approved fixture",
            "publisher": "Official Publisher",
            "source_url": "https://example.invalid/source",
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
            }
        ],
    }


def test_catalog_and_territory_values_expose_source_metadata(tmp_path: Path) -> None:
    installed = install_market_indicator_artifact(artifact(), tmp_path)
    checksum = str(installed["checksum_sha256"])
    app.dependency_overrides[get_market_indicator_directory] = lambda: tmp_path
    try:
        client = TestClient(app)
        catalog = client.get("/api/v1/market-indicators/artifacts")
        assert catalog.status_code == 200
        assert catalog.json()[0]["checksum_sha256"] == checksum
        values = client.get(
            f"/api/v1/market-indicators/artifacts/{checksum}/territories/galway-city"
        )
        assert values.status_code == 200
        assert values.json()[0]["source"]["publisher"] == "Official Publisher"
        assert values.json()[0]["unit"] == "businesses"
    finally:
        app.dependency_overrides.clear()


def test_missing_territory_values_are_empty_not_zero(tmp_path: Path) -> None:
    installed = install_market_indicator_artifact(artifact(), tmp_path)
    checksum = str(installed["checksum_sha256"])
    app.dependency_overrides[get_market_indicator_directory] = lambda: tmp_path
    try:
        response = TestClient(app).get(
            f"/api/v1/market-indicators/artifacts/{checksum}/territories/missing"
        )
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()
