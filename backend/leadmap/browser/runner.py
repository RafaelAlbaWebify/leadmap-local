import argparse
import signal
from collections.abc import Sequence
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leadmap-assisted-browser")
    parser.add_argument("--profile-directory", type=Path, required=True)
    parser.add_argument("--start-url", default="about:blank")
    return parser


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
            page.wait_for_timeout(250)
        context.close()
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
