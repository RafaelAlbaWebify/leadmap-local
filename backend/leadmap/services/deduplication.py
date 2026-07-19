from collections.abc import Iterable

from backend.leadmap.domain.models import ObservedBusiness


def deduplicate_observations(
    observations: Iterable[ObservedBusiness],
) -> list[ObservedBusiness]:
    seen: set[tuple[str, str]] = set()
    unique: list[ObservedBusiness] = []

    for observation in observations:
        identity = (observation.provider.casefold(), observation.provider_key.casefold())
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(observation)

    return unique
