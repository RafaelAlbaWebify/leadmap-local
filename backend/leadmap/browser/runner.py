import argparse
import signal
import sys
from collections.abc import Sequence
from pathlib import Path

from .google_maps import (
    VisiblePageSelectorDrift,
    VisiblePageUnsupported,
    capture_visible_google_maps_cards,
)
from .protocol import (
    BrowserProtocolError,
    ProtocolResponse,
    decode_request,
    encode_response,
    write_message,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leadmap-assisted-browser")
    parser.add_argument("--profile-directory", type=Path, required=True)
    parser.add_argument("--start-url", default="about:blank")
    return parser


def _respond(response: ProtocolResponse) -> None:
    write_message(sys.stdout, encode_response(response))


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
                if request.command != "capture_visible":
                    _respond(
                        ProtocolResponse(
                            request_id=request.request_id,
                            ok=False,
                            error_code="unsupported_command",
                            error_message="The browser command is not supported.",
                        )
                    )
                    continue
                max_results = request.payload.get("max_results")
                if not isinstance(max_results, int) or isinstance(
                    max_results,
                    bool,
                ):
                    raise BrowserProtocolError("max_results must be an integer.")
                candidates = capture_visible_google_maps_cards(
                    page,
                    max_results=max_results,
                )
                _respond(
                    ProtocolResponse(
                        request_id=request.request_id,
                        ok=True,
                        result={"candidates": candidates},
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
                            "The visible browser could not capture the current results."
                        ),
                    )
                )
        context.close()
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
