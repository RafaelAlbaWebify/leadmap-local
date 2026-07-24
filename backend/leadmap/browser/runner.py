import argparse
import signal
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from .google_maps import (
    VisiblePageSelectorDrift,
    VisiblePageUnsupported,
    capture_visible_google_maps_cards,
    traverse_google_maps_results,
)
from .protocol import (
    BrowserProtocolError,
    ProtocolResponse,
    decode_request,
    encode_response,
    write_message,
)
from .traversal import TraversalLimits


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leadmap-assisted-browser")
    parser.add_argument("--profile-directory", type=Path, required=True)
    parser.add_argument("--start-url", default="about:blank")
    return parser


def _respond(response: ProtocolResponse) -> None:
    write_message(sys.stdout, encode_response(response))


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise BrowserProtocolError(f"{key} must be an integer.")
    return value


def _required_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise BrowserProtocolError(f"{key} must be numeric.")
    return float(value)


def _handle_capture_visible(page: object, payload: dict[str, object]) -> dict[str, object]:
    max_results = _required_int(payload, "max_results")
    candidates = capture_visible_google_maps_cards(page, max_results=max_results)
    return {"candidates": candidates}


def _handle_collect_bounded(page: object, payload: dict[str, object]) -> dict[str, object]:
    query_text = payload.get("query_text")
    if not isinstance(query_text, str) or not query_text.strip():
        raise BrowserProtocolError("query_text must be a non-empty string.")
    query_sequence = _required_int(payload, "query_sequence")
    limits = TraversalLimits(
        max_cards=_required_int(payload, "max_cards"),
        max_scrolls=_required_int(payload, "max_scrolls"),
        max_elapsed_seconds=_required_float(payload, "max_elapsed_seconds"),
        max_stagnant_scrolls=_required_int(payload, "max_stagnant_scrolls"),
    )
    result = traverse_google_maps_results(
        page,
        query_text=query_text,
        query_sequence=query_sequence,
        limits=limits,
    )
    return {
        "candidates": [asdict(observation.candidate) for observation in result.observations],
        "progress": asdict(result.progress),
    }


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Install LeadMap with the browser optional dependency."
        ) from exc

    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(args.profile_directory),
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(str(args.start_url))
        while not stopping and context.pages:
            line = sys.stdin.readline()
            if line == "":
                break
            request_id = "unknown"
            try:
                request = decode_request(line)
                request_id = request.request_id
                if request.command == "capture_visible":
                    result = _handle_capture_visible(page, request.payload)
                elif request.command == "collect_bounded":
                    result = _handle_collect_bounded(page, request.payload)
                else:
                    _respond(
                        ProtocolResponse(
                            request_id=request.request_id,
                            ok=False,
                            error_code="unsupported_command",
                            error_message="The browser command is not supported.",
                        )
                    )
                    continue
                _respond(
                    ProtocolResponse(
                        request_id=request.request_id,
                        ok=True,
                        result=result,
                    )
                )
            except VisiblePageUnsupported as exc:
                _respond(
                    ProtocolResponse(
                        request_id=request_id,
                        ok=False,
                        error_code="unsupported_page",
                        error_message=str(exc),
                    )
                )
            except VisiblePageSelectorDrift as exc:
                _respond(
                    ProtocolResponse(
                        request_id=request_id,
                        ok=False,
                        error_code="selector_drift",
                        error_message=str(exc),
                    )
                )
            except (BrowserProtocolError, ValueError) as exc:
                _respond(
                    ProtocolResponse(
                        request_id=request_id,
                        ok=False,
                        error_code="invalid_request",
                        error_message=str(exc),
                    )
                )
            except Exception:
                _respond(
                    ProtocolResponse(
                        request_id=request_id,
                        ok=False,
                        error_code="browser_error",
                        error_message=(
                            "The visible browser could not collect the current results."
                        ),
                    )
                )
        context.close()
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
