from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from .sessions import VisibleCandidate


class TraversalStopReason(StrEnum):
    END_OF_LIST = "end_of_list"
    NO_NEW_RESULTS = "no_new_results"
    MAX_CARDS = "max_cards"
    MAX_SCROLLS = "max_scrolls"
    TIMEOUT = "timeout"
    OPERATOR_STOP = "operator_stop"
    PROVIDER_ERROR = "provider_error"


@dataclass(frozen=True, slots=True)
class TraversalLimits:
    max_cards: int = 100
    max_scrolls: int = 40
    max_elapsed_seconds: float = 90.0
    max_stagnant_scrolls: int = 3

    def __post_init__(self) -> None:
        if self.max_cards < 1:
            raise ValueError("max_cards must be at least 1.")
        if self.max_scrolls < 0:
            raise ValueError("max_scrolls cannot be negative.")
        if self.max_elapsed_seconds <= 0:
            raise ValueError("max_elapsed_seconds must be greater than 0.")
        if self.max_stagnant_scrolls < 1:
            raise ValueError("max_stagnant_scrolls must be at least 1.")


@dataclass(frozen=True, slots=True)
class TraversalObservation:
    candidate: VisibleCandidate
    query_text: str
    query_sequence: int
    result_rank: int
    first_seen_scroll_step: int
    captured_at: str


@dataclass(frozen=True, slots=True)
class TraversalProgress:
    query_text: str
    query_sequence: int
    scroll_step: int
    unique_cards: int
    stagnant_scrolls: int
    elapsed_seconds: float
    stop_reason: TraversalStopReason | None = None


class OrderedCardAccumulator:
    def __init__(self, *, query_text: str, query_sequence: int, limits: TraversalLimits) -> None:
        if not query_text.strip():
            raise ValueError("query_text cannot be blank.")
        if query_sequence < 1:
            raise ValueError("query_sequence must be at least 1.")
        self._query_text = query_text.strip()
        self._query_sequence = query_sequence
        self._limits = limits
        self._observations: list[TraversalObservation] = []
        self._seen_provider_keys: set[str] = set()
        self._stagnant_scrolls = 0

    @property
    def observations(self) -> tuple[TraversalObservation, ...]:
        return tuple(self._observations)

    @property
    def stagnant_scrolls(self) -> int:
        return self._stagnant_scrolls

    def add_batch(
        self,
        candidates: list[VisibleCandidate],
        *,
        scroll_step: int,
        captured_at: str,
    ) -> int:
        if scroll_step < 0:
            raise ValueError("scroll_step cannot be negative.")
        added = 0
        for candidate in candidates:
            provider_key = candidate.provider_key.strip()
            if not provider_key or provider_key in self._seen_provider_keys:
                continue
            if len(self._observations) >= self._limits.max_cards:
                break
            self._seen_provider_keys.add(provider_key)
            rank = len(self._observations) + 1
            self._observations.append(
                TraversalObservation(
                    candidate=replace(candidate, provider_key=provider_key),
                    query_text=self._query_text,
                    query_sequence=self._query_sequence,
                    result_rank=rank,
                    first_seen_scroll_step=scroll_step,
                    captured_at=captured_at,
                )
            )
            added += 1
        self._stagnant_scrolls = 0 if added else self._stagnant_scrolls + 1
        return added

    def evaluate_stop(
        self,
        *,
        scroll_step: int,
        elapsed_seconds: float,
        end_of_list: bool = False,
        operator_stop: bool = False,
        provider_error: bool = False,
    ) -> TraversalStopReason | None:
        if operator_stop:
            return TraversalStopReason.OPERATOR_STOP
        if provider_error:
            return TraversalStopReason.PROVIDER_ERROR
        if end_of_list:
            return TraversalStopReason.END_OF_LIST
        if len(self._observations) >= self._limits.max_cards:
            return TraversalStopReason.MAX_CARDS
        if elapsed_seconds >= self._limits.max_elapsed_seconds:
            return TraversalStopReason.TIMEOUT
        if scroll_step >= self._limits.max_scrolls:
            return TraversalStopReason.MAX_SCROLLS
        if self._stagnant_scrolls >= self._limits.max_stagnant_scrolls:
            return TraversalStopReason.NO_NEW_RESULTS
        return None

    def progress(
        self,
        *,
        scroll_step: int,
        elapsed_seconds: float,
        stop_reason: TraversalStopReason | None = None,
    ) -> TraversalProgress:
        return TraversalProgress(
            query_text=self._query_text,
            query_sequence=self._query_sequence,
            scroll_step=scroll_step,
            unique_cards=len(self._observations),
            stagnant_scrolls=self._stagnant_scrolls,
            elapsed_seconds=elapsed_seconds,
            stop_reason=stop_reason,
        )
