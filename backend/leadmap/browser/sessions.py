from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4


class AssistedSessionState(StrEnum):
    IDLE = "idle"
    LAUNCHING = "launching"
    AWAITING_OPERATOR = "awaiting_operator"
    READY = "ready"
    CAPTURING = "capturing"
    REVIEW = "review"
    STOPPED = "stopped"
    FAILED = "failed"


ACTIVE_STATES = {
    AssistedSessionState.LAUNCHING,
    AssistedSessionState.AWAITING_OPERATOR,
    AssistedSessionState.READY,
    AssistedSessionState.CAPTURING,
    AssistedSessionState.REVIEW,
}


@dataclass(frozen=True, slots=True)
class VisibleCandidate:
    candidate_id: str
    provider_key: str
    displayed_name: str
    normalized_name: str
    category: str | None = None
    address_text: str | None = None
    phone: str | None = None
    website: str | None = None
    source_url: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    raw_evidence: str | None = None
    included: bool = True


@dataclass(frozen=True, slots=True)
class AssistedSession:
    session_id: str | None
    state: AssistedSessionState
    territory_id: str | None = None
    query_template_id: str | None = None
    start_url: str | None = None
    error: str | None = None
    candidates: tuple[VisibleCandidate, ...] = ()


class AssistedSessionConflict(RuntimeError):
    pass


class AssistedSessionTransitionError(RuntimeError):
    pass


class VisibleCaptureUnsupported(RuntimeError):
    pass


class AssistedBrowserProvider(Protocol):
    def launch(self, *, start_url: str) -> None: ...

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]: ...

    def stop(self) -> None: ...


_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _SPACE_RE.sub(" ", value).strip()
    return cleaned or None


def _normalize_name(value: str) -> str:
    cleaned = _clean_text(value) or ""
    return _NON_ALNUM_RE.sub(" ", cleaned.casefold()).strip()


def _normalize_url(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    parsed = urlsplit(cleaned if "://" in cleaned else f"https://{cleaned}")
    if not parsed.netloc:
        return cleaned
    path = parsed.path.rstrip("/") or ""
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def normalize_and_deduplicate_candidates(
    candidates: list[VisibleCandidate],
    *,
    max_results: int,
) -> tuple[VisibleCandidate, ...]:
    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    result: list[VisibleCandidate] = []
    seen_provider_keys: set[str] = set()
    seen_identity: set[tuple[str, str, str]] = set()

    for candidate in candidates:
        name = _clean_text(candidate.displayed_name)
        provider_key = _clean_text(candidate.provider_key)
        if name is None or provider_key is None:
            continue

        normalized_name = _normalize_name(name)
        address = _clean_text(candidate.address_text)
        phone = _clean_text(candidate.phone)
        website = _normalize_url(candidate.website)
        source_url = _normalize_url(candidate.source_url)
        identity = (normalized_name, phone or "", website or address or "")

        if provider_key in seen_provider_keys or identity in seen_identity:
            continue

        seen_provider_keys.add(provider_key)
        seen_identity.add(identity)
        result.append(
            VisibleCandidate(
                candidate_id=candidate.candidate_id or str(uuid4()),
                provider_key=provider_key,
                displayed_name=name,
                normalized_name=normalized_name,
                category=_clean_text(candidate.category),
                address_text=address,
                phone=phone,
                website=website,
                source_url=source_url,
                latitude=_clean_text(candidate.latitude),
                longitude=_clean_text(candidate.longitude),
                raw_evidence=_clean_text(candidate.raw_evidence),
                included=candidate.included,
            )
        )
        if len(result) >= max_results:
            break

    return tuple(result)


class SubprocessPlaywrightProvider:
    def __init__(self, *, profile_directory: Path = Path("browser-profile")) -> None:
        self._profile_directory = profile_directory
        self._process: subprocess.Popen[bytes] | None = None

    def launch(self, *, start_url: str) -> None:
        if self._process is not None and self._process.poll() is None:
            raise AssistedSessionConflict("A visible browser process is already active.")
        self._profile_directory.mkdir(parents=True, exist_ok=True)
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "backend.leadmap.browser.runner",
                "--profile-directory",
                str(self._profile_directory),
                "--start-url",
                start_url,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self._process.poll() is not None:
            raise RuntimeError("The visible browser process exited during launch.")

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
        raise VisibleCaptureUnsupported(
            "Visible-result capture is not connected to the browser process yet. "
            "Keep the session open and install the provider adapter before retrying."
        )

    def stop(self) -> None:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


class AssistedSessionManager:
    def __init__(self, provider: AssistedBrowserProvider) -> None:
        self._provider = provider
        self._session = AssistedSession(session_id=None, state=AssistedSessionState.IDLE)

    def snapshot(self) -> AssistedSession:
        return self._session

    def launch(
        self,
        *,
        territory_id: str,
        query_template_id: str,
        start_url: str = "about:blank",
    ) -> AssistedSession:
        if self._session.state in ACTIVE_STATES:
            raise AssistedSessionConflict("An assisted browser session is already active.")

        session = AssistedSession(
            session_id=str(uuid4()),
            state=AssistedSessionState.LAUNCHING,
            territory_id=territory_id,
            query_template_id=query_template_id,
            start_url=start_url,
        )
        self._session = session
        try:
            self._provider.launch(start_url=start_url)
        except Exception as exc:
            self._session = replace(session, state=AssistedSessionState.FAILED, error=str(exc))
            raise

        self._session = replace(session, state=AssistedSessionState.AWAITING_OPERATOR)
        return self._session

    def mark_ready(self, session_id: str) -> AssistedSession:
        self._require_current(session_id)
        if self._session.state is not AssistedSessionState.AWAITING_OPERATOR:
            raise AssistedSessionTransitionError(
                "The session can be marked ready only while awaiting the operator."
            )
        self._session = replace(self._session, state=AssistedSessionState.READY)
        return self._session

    def capture_visible(self, session_id: str, *, max_results: int) -> AssistedSession:
        self._require_current(session_id)
        if self._session.state is not AssistedSessionState.READY:
            raise AssistedSessionTransitionError(
                "Visible results can be captured only after the operator marks the browser ready."
            )
        self._session = replace(self._session, state=AssistedSessionState.CAPTURING, error=None)
        try:
            captured = self._provider.capture_visible(max_results=max_results)
            candidates = normalize_and_deduplicate_candidates(
                captured,
                max_results=max_results,
            )
        except Exception as exc:
            self._session = replace(
                self._session,
                state=AssistedSessionState.READY,
                error=str(exc),
            )
            raise
        self._session = replace(
            self._session,
            state=AssistedSessionState.REVIEW,
            candidates=candidates,
            error=None,
        )
        return self._session

    def set_candidate_included(
        self,
        session_id: str,
        candidate_id: str,
        *,
        included: bool,
    ) -> AssistedSession:
        self._require_current(session_id)
        if self._session.state is not AssistedSessionState.REVIEW:
            raise AssistedSessionTransitionError("Candidates can be edited only during review.")
        found = False
        updated: list[VisibleCandidate] = []
        for candidate in self._session.candidates:
            if candidate.candidate_id == candidate_id:
                found = True
                updated.append(replace(candidate, included=included))
            else:
                updated.append(candidate)
        if not found:
            raise AssistedSessionTransitionError("The candidate does not exist.")
        self._session = replace(self._session, candidates=tuple(updated))
        return self._session

    def stop(self, session_id: str | None = None) -> AssistedSession:
        if self._session.session_id is None:
            return self._session
        if session_id is not None:
            self._require_current(session_id)
        if self._session.state in {AssistedSessionState.STOPPED, AssistedSessionState.FAILED}:
            return self._session

        self._provider.stop()
        self._session = replace(self._session, state=AssistedSessionState.STOPPED)
        return self._session

    def _require_current(self, session_id: str) -> None:
        if self._session.session_id != session_id:
            raise AssistedSessionTransitionError("The assisted browser session does not exist.")
