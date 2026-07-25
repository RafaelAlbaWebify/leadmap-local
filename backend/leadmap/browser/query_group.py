from __future__ import annotations

from dataclasses import dataclass

from .sessions import VisibleCandidate
from .traversal import TraversalObservation, TraversalResult, TraversalStopReason


@dataclass(frozen=True, slots=True)
class QueryRunSummary:
    query_text: str
    query_sequence: int
    observation_count: int
    unique_businesses_added: int
    stop_reason: TraversalStopReason


@dataclass(frozen=True, slots=True)
class AggregateBusiness:
    identity_key: str
    representative: VisibleCandidate
    observations: tuple[TraversalObservation, ...]
    first_seen_order: int

    @property
    def appearance_count(self) -> int:
        return len(self.observations)


@dataclass(frozen=True, slots=True)
class QueryGroupSnapshot:
    businesses: tuple[AggregateBusiness, ...]
    query_runs: tuple[QueryRunSummary, ...]
    total_observations: int

    @property
    def unique_businesses(self) -> int:
        return len(self.businesses)

    @property
    def duplicate_appearances(self) -> int:
        return self.total_observations - self.unique_businesses


class QueryGroupAggregator:
    def __init__(self) -> None:
        self._businesses: list[AggregateBusiness] = []
        self._business_indexes: dict[str, int] = {}
        self._query_runs: list[QueryRunSummary] = []
        self._total_observations = 0

    def add_result(self, result: TraversalResult) -> QueryRunSummary:
        progress = result.progress
        if progress.stop_reason is None:
            raise ValueError("A completed query result must include a stop reason.")
        if any(run.query_sequence == progress.query_sequence for run in self._query_runs):
            raise ValueError("The query sequence has already been aggregated.")

        added_businesses = 0
        for observation in result.observations:
            if observation.query_sequence != progress.query_sequence:
                raise ValueError("Observation query sequence does not match result progress.")
            identity_key = _business_identity(observation.candidate)
            index = self._business_indexes.get(identity_key)
            if index is None:
                index = len(self._businesses)
                self._business_indexes[identity_key] = index
                self._businesses.append(
                    AggregateBusiness(
                        identity_key=identity_key,
                        representative=observation.candidate,
                        observations=(observation,),
                        first_seen_order=index + 1,
                    )
                )
                added_businesses += 1
            else:
                current = self._businesses[index]
                self._businesses[index] = AggregateBusiness(
                    identity_key=current.identity_key,
                    representative=current.representative,
                    observations=(*current.observations, observation),
                    first_seen_order=current.first_seen_order,
                )
            self._total_observations += 1

        summary = QueryRunSummary(
            query_text=progress.query_text,
            query_sequence=progress.query_sequence,
            observation_count=len(result.observations),
            unique_businesses_added=added_businesses,
            stop_reason=progress.stop_reason,
        )
        self._query_runs.append(summary)
        return summary

    def snapshot(self) -> QueryGroupSnapshot:
        return QueryGroupSnapshot(
            businesses=tuple(self._businesses),
            query_runs=tuple(self._query_runs),
            total_observations=self._total_observations,
        )


def _business_identity(candidate: VisibleCandidate) -> str:
    provider_key = candidate.provider_key.strip()
    if provider_key:
        return f"provider:{provider_key}"

    normalized_name = candidate.normalized_name.strip()
    discriminator = (
        (candidate.phone or "").strip()
        or (candidate.website or "").strip().casefold()
        or (candidate.address_text or "").strip().casefold()
    )
    if not normalized_name or not discriminator:
        raise ValueError("A cross-query business requires a provider key or fallback identity.")
    return f"fallback:{normalized_name}|{discriminator}"
