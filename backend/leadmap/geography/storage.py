import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from .imports import BoundaryImportArtifact
from .validation import BoundaryValidationError

ARTIFACT_SCHEMA_VERSION = "1"


@dataclass(frozen=True, slots=True)
class StoredBoundaryArtifact:
    path: Path
    created: bool
    idempotency_key: str


def _artifact_document(artifact: BoundaryImportArtifact) -> dict[str, object]:
    source = asdict(artifact.source)
    source["retrieved_at"] = artifact.source.retrieved_at.isoformat()
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "idempotency_key": artifact.idempotency_key,
        "checksum_sha256": artifact.checksum_sha256,
        "source": source,
        "feature_count": artifact.collection.feature_count,
        "boundaries": [asdict(boundary) for boundary in artifact.collection.boundaries],
    }


def _encoded_document(artifact: BoundaryImportArtifact) -> bytes:
    document = _artifact_document(artifact)
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _validate_existing(path: Path, artifact: BoundaryImportArtifact) -> None:
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryValidationError(
            f"Existing geographic artifact is unreadable: {path}."
        ) from exc

    if not isinstance(existing, dict):
        raise BoundaryValidationError(f"Existing geographic artifact has an invalid root: {path}.")
    if existing.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise BoundaryValidationError(f"Existing geographic artifact schema is unsupported: {path}.")
    if existing.get("idempotency_key") != artifact.idempotency_key:
        raise BoundaryValidationError(f"Existing geographic artifact identity does not match: {path}.")
    if existing.get("checksum_sha256") != artifact.checksum_sha256:
        raise BoundaryValidationError(f"Existing geographic artifact checksum does not match: {path}.")


def store_boundary_artifact(
    artifact: BoundaryImportArtifact,
    *,
    directory: Path,
) -> StoredBoundaryArtifact:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"boundaries-{artifact.checksum_sha256}.json"

    if target.exists():
        _validate_existing(target, artifact)
        return StoredBoundaryArtifact(
            path=target,
            created=False,
            idempotency_key=artifact.idempotency_key,
        )

    temporary = directory / f".{target.name}.{uuid4().hex}.tmp"
    try:
        temporary.write_bytes(_encoded_document(artifact))
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)

    return StoredBoundaryArtifact(
        path=target,
        created=True,
        idempotency_key=artifact.idempotency_key,
    )
