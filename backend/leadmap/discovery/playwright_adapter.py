"""Boundary for the future assisted, headed browser session.

This module deliberately contains no Google Maps selectors yet. Selector implementation
must be based on captured diagnostics from a user-approved session and covered by saved
fixtures before being enabled.
"""

from collections.abc import Sequence

from backend.leadmap.domain.models import ObservedBusiness

from .provider import SearchRequest


class PlaywrightDiscoveryProvider:
    async def capture_candidates(self, request: SearchRequest) -> Sequence[ObservedBusiness]:
        raise NotImplementedError(
            "Live browser capture is not enabled. Use FixtureDiscoveryProvider until "
            "the assisted-session states and parser fixtures are approved."
        )
