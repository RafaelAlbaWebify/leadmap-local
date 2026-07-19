import json
from datetime import UTC, datetime
from pathlib import Path

from backend.leadmap.domain.models import ObservedBusiness

from .provider import SearchRequest


class FixtureDiscoveryProvider:
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    async def capture_candidates(self, request: SearchRequest) -> list[ObservedBusiness]:
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        records = [
            ObservedBusiness(
                provider="fixture",
                provider_key=item["provider_key"],
                name=item["name"],
                category=item["category"],
                locality=item["locality"],
                postal_area=item.get("postal_area"),
                website=item.get("website"),
                phone=item.get("phone"),
                source_url=item.get("source_url"),
                observed_at=datetime.fromisoformat(item["observed_at"]).astimezone(UTC),
            )
            for item in payload
            if request.phrase.casefold() in item["matched_phrases"]
            and request.country_code == item["country_code"]
        ]
        return records[: request.max_results]
