from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.leadmap.geography.diagnostics import build_geography_diagnostics  # noqa: E402
from backend.leadmap.geography.validation import BoundaryValidationError  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare an installed canonical geography artifact with its derived map payload."
    )
    parser.add_argument(
        "artifact",
        type=Path,
        help="Path to a canonical geography artifact JSON file.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        document = json.loads(args.artifact.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise BoundaryValidationError("Geographic artifact root must be a JSON object.")
        result = build_geography_diagnostics(document).to_dict()
    except (OSError, json.JSONDecodeError, BoundaryValidationError) as exc:
        raise SystemExit(f"Geography diagnostics failed: {exc}") from exc

    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
