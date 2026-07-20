import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from .models import BoundaryCollection
from .validation import BoundaryValidationError, validate_feature_collection

IMPORT_CONTRACT_VERSION = "1"


@dataclass(frozen=True, slots=True)
class BoundarySourceMetadata:
    dataset_title: str
    publisher: str
    licence: str
    edition_year: int
    source_url: str
    retrieved_at: datetime
    contract_version: str = IMPORT_CONTRACT_VERSION


@dataclass(frozen=True, slots=True)
class BoundaryImportArtifact:
    source: BoundarySourceMetadata
    checksum_sha256: str
    collection: BoundaryCollection

    @property
    def idempotency_key(self) -> str:
        return f"{self.source.contract_version}:{self.checksum_sha256}"


def _decode_json(raw_data: bytes) -> object:
    try:
        text = raw_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BoundaryValidationError("Boundary source must be UTF-8 encoded JSON.") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise BoundaryValidationError(
            f"Boundary source is not valid JSON at line {exc.lineno}, column {exc.colno}."
        ) from exc


def import_boundary_bytes(
    raw_data: bytes,
    *,
    source: BoundarySourceMetadata,
    id_field: str,
    name_field: str,
    expected_feature_count: int | None = None,
) -> BoundaryImportArtifact:
    if not raw_data:
        raise BoundaryValidationError("Boundary source file is empty.")

    collection = validate_feature_collection(
        _decode_json(raw_data),
        id_field=id_field,
        name_field=name_field,
        expected_feature_count=expected_feature_count,
    )
    checksum = hashlib.sha256(raw_data).hexdigest()
    return BoundaryImportArtifact(
        source=source,
        checksum_sha256=checksum,
        collection=collection,
    )
