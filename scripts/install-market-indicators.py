from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.leadmap.market_indicators import (
    MarketIndicatorValidationError,
    install_market_indicator_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and install an approved market indicator artifact."
    )
    parser.add_argument("artifact", type=Path, help="Path to the approved JSON artifact.")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path("data/market-indicators"),
        help="Checksum-addressed installation directory.",
    )
    args = parser.parse_args()
    try:
        document = json.loads(args.artifact.read_text(encoding="utf-8"))
        installed = install_market_indicator_artifact(document, args.directory)
    except (OSError, json.JSONDecodeError, MarketIndicatorValidationError) as exc:
        print(f"Market indicator import failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "checksum_sha256": installed["checksum_sha256"],
                "record_count": len(installed["records"]),
                "directory": str(args.directory),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
