from pathlib import Path

import pytest

from backend.leadmap.discovery.fixture_provider import FixtureDiscoveryProvider
from backend.leadmap.discovery.provider import SearchRequest
from backend.leadmap.services.deduplication import deduplicate_observations


@pytest.mark.asyncio
async def test_fixture_capture_and_deduplication() -> None:
    provider = FixtureDiscoveryProvider(Path("backend/tests/fixtures/irish_businesses.json"))
    observations = await provider.capture_candidates(
        SearchRequest(
            territory_name="Galway City",
            country_code="IE",
            phrase="accountant",
            max_results=20,
        )
    )

    unique = deduplicate_observations(observations)

    assert len(observations) == 3
    assert len(unique) == 2
    assert unique[0].postal_area == "H91"
    assert unique[1].website is None
