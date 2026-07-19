from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from backend.leadmap.domain.models import ObservedBusiness


@dataclass(frozen=True, slots=True)
class SearchRequest:
    territory_name: str
    country_code: str
    phrase: str
    max_results: int = 20


class DiscoveryProvider(Protocol):
    async def capture_candidates(self, request: SearchRequest) -> Sequence[ObservedBusiness]:
        """Capture candidates for one explicitly approved search."""
        ...
