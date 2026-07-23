from __future__ import annotations

import queue
import subprocess
import sys
import threading
from dataclasses import fields
from pathlib import Path
from typing import Any
from uuid import uuid4

from .protocol import (
    BrowserProtocolError,
    ProtocolRequest,
    decode_response,
    encode_request,
    write_message,
)
from .sessions import (
    AssistedSessionConflict,
    VisibleCandidate,
    VisibleCaptureUnsupported,
)


class SubprocessPlaywrightProvider:
    def __init__(
        self,
        *,
        profile_directory: Path = Path("browser-profile"),
        response_timeout_seconds: float = 10.0,
    ) -> None:
        self._profile_directory = profile_directory
        self._response_timeout_seconds = response_timeout_seconds
        self._process: subprocess.Popen[str] | None = None

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
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        if self._process.poll() is not None:
            raise RuntimeError("The visible browser process exited during launch.")

    def capture_visible(self, *, max_results: int) -> list[VisibleCandidate]:
        process = self._require_running_process()
        if process.stdin is None or process.stdout is None:
            raise VisibleCaptureUnsupported(
                "The visible browser communication channel is unavailable. "
                "Stop and relaunch the session."
            )
        request_id = str(uuid4())
        write_message(
            process.stdin,
            encode_request(
                ProtocolRequest(
                    request_id=request_id,
                    command="capture_visible",
                    payload={"max_results": max_results},
                )
            ),
        )
        line = self._readline_with_timeout(process.stdout)
        response = decode_response(line, expected_request_id=request_id)
        if not response.ok:
            raise VisibleCaptureUnsupported(
                response.error_message or "Visible-result capture failed."
            )
        raw_candidates = (response.result or {}).get("candidates")
        if not isinstance(raw_candidates, list):
            raise BrowserProtocolError("Browser protocol candidates must be a list.")
        if len(raw_candidates) > max_results:
            raise BrowserProtocolError("Browser process returned more candidates than requested.")
        allowed = {field.name for field in fields(VisibleCandidate)}
        candidates: list[VisibleCandidate] = []
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                raise BrowserProtocolError("Browser protocol candidate must be an object.")
            unknown = set(raw_candidate) - allowed
            if unknown:
                raise BrowserProtocolError("Browser protocol candidate contains unknown fields.")
            candidates.append(VisibleCandidate(**_candidate_values(raw_candidate)))
        return candidates

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

    def _require_running_process(self) -> subprocess.Popen[str]:
        process = self._process
        if process is None or process.poll() is not None:
            raise VisibleCaptureUnsupported(
                "The visible browser process is not running. Stop and relaunch the session."
            )
        return process

    def _readline_with_timeout(self, stream: Any) -> str:
        responses: queue.Queue[str | BaseException] = queue.Queue(maxsize=1)

        def read() -> None:
            try:
                responses.put(stream.readline())
            except BaseException as exc:  # pragma: no cover - defensive pipe boundary
                responses.put(exc)

        threading.Thread(target=read, daemon=True).start()
        try:
            value = responses.get(timeout=self._response_timeout_seconds)
        except queue.Empty as exc:
            raise VisibleCaptureUnsupported(
                "The visible browser did not respond in time. Keep it open and retry, "
                "or stop and relaunch."
            ) from exc
        if isinstance(value, BaseException):
            raise VisibleCaptureUnsupported(
                "The visible browser response could not be read. Stop and relaunch the session."
            ) from value
        if value == "":
            raise VisibleCaptureUnsupported(
                "The visible browser process exited before capture completed. "
                "Stop and relaunch the session."
            )
        return value


def _candidate_values(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(raw.get("candidate_id") or ""),
        "provider_key": str(raw.get("provider_key") or ""),
        "displayed_name": str(raw.get("displayed_name") or ""),
        "normalized_name": str(raw.get("normalized_name") or ""),
        "category": raw.get("category"),
        "address_text": raw.get("address_text"),
        "phone": raw.get("phone"),
        "website": raw.get("website"),
        "source_url": raw.get("source_url"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "raw_evidence": raw.get("raw_evidence"),
        "included": bool(raw.get("included", True)),
    }
