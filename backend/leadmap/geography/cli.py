import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .imports import BoundarySourceMetadata, import_boundary_bytes
from .storage import store_boundary_artifact
from .validation import BoundaryValidationError


def _retrieved_at(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("retrieved-at must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None:
        raise argparse.ArgumentTypeError("retrieved-at must include a UTC offset")
    return timestamp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leadmap-import-geography",
        description="Validate and store a downloaded GeoJSON boundary source.",
    )
    parser.add_argument("source_file", type=Path)
    parser.add_argument("--artifact-directory", type=Path, default=Path("data/geography"))
    parser.add_argument("--dataset-title", required=True)
    parser.add_argument("--publisher", required=True)
    parser.add_argument("--licence", required=True)
    parser.add_argument("--edition-year", required=True, type=int)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--retrieved-at", required=True, type=_retrieved_at)
    parser.add_argument("--id-field", required=True)
    parser.add_argument("--name-field", required=True)
    parser.add_argument("--expected-feature-count", type=int)
    return parser


def run_import(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw_data = args.source_file.read_bytes()
        artifact = import_boundary_bytes(
            raw_data,
            source=BoundarySourceMetadata(
                dataset_title=args.dataset_title,
                publisher=args.publisher,
                licence=args.licence,
                edition_year=args.edition_year,
                source_url=args.source_url,
                retrieved_at=args.retrieved_at,
            ),
            id_field=args.id_field,
            name_field=args.name_field,
            expected_feature_count=args.expected_feature_count,
        )
        stored = store_boundary_artifact(artifact, directory=args.artifact_directory)
    except (OSError, BoundaryValidationError) as exc:
        print(f"Geography import failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "artifact_path": str(stored.path),
                "checksum_sha256": artifact.checksum_sha256,
                "created": stored.created,
                "feature_count": artifact.collection.feature_count,
                "idempotency_key": stored.idempotency_key,
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> None:
    raise SystemExit(run_import())


if __name__ == "__main__":
    main()
