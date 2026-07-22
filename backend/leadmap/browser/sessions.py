from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import uuid4


class AssistedSessionState(StrEnum):
    IDLE = "idle"
    LAUNCHING = "launching"
    AWAITING_OPERATOR = "awaiting_operator"
    READY = "ready"
    STOPPED = "stopped"
    FAILED = "failed"


ACTIVE_STATES = {
    AssistedSessionState.LAUNCHING,
    AssistedSessionState.AWAITING_OPERATOR,
    AssistedSessionState.READY,
}


@dataclass(frozen=True, slots=True)
class AssistedSession:
    session_id: str | None
    state: AssistedSessionState
    territory_id: str | None = None
    query_template_id: str | None = None
    start_url: str | None = None
    error: str | None = None


class AssistedSessionConflict(RuntimeError):
    pass


class AssistedSessionTransitionError(RuntimeError):
    pass


class AssistedBrowserProvider(Protocol):
    def launch(self, *, start_url: str) -> None: ...

    def stop(self) -> None: ...


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
            self._session = replace(
                session,
                state=AssistedSessionState.FAILED,
                error=str(exc),
            )
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
