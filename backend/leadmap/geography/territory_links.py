import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from .validation import BoundaryValidationError

LINKS_SCHEMA_VERSION = "1"
LINKS_FILENAME = "territory-boundary-links.json"


@dataclass(frozen=True, slots=True)
class TerritoryBoundaryLink:
    territory_id: str
    checksum_sha256: str
    boundary_external_id: str
    boundary_name: str


def _links_path(directory: Path) -> Path:
    return directory / LINKS_FILENAME


def _read_document(directory: Path) -> dict[str, object]:
    path = _links_path(directory)
    if not path.exists():
        return {"schema_version": LINKS_SCHEMA_VERSION, "links": {}}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BoundaryValidationError(f"Territory link store is unreadable: {path}.") from exc
    if not isinstance(document, dict):
        raise BoundaryValidationError(f"Territory link store has an invalid root: {path}.")
    if document.get("schema_version") != LINKS_SCHEMA_VERSION:
        raise BoundaryValidationError(f"Territory link store schema is unsupported: {path}.")
    links = document.get("links")
    if not isinstance(links, dict):
        raise BoundaryValidationError(f"Territory link store has an invalid links collection: {path}.")
    return document


def list_territory_boundary_links(*, directory: Path) -> list[TerritoryBoundaryLink]:
    document = _read_document(directory)
    links = document["links"]
    assert isinstance(links, dict)
    results: list[TerritoryBoundaryLink] = []
    for territory_id, value in links.items():
        if not isinstance(territory_id, str) or not isinstance(value, dict):
            raise BoundaryValidationError("Territory link store contains an invalid entry.")
        try:
            results.append(
                TerritoryBoundaryLink(
                    territory_id=territory_id,
                    checksum_sha256=str(value["checksum_sha256"]),
                    boundary_external_id=str(value["boundary_external_id"]),
                    boundary_name=str(value["boundary_name"]),
                )
            )
        except KeyError as exc:
            raise BoundaryValidationError("Territory link store contains an incomplete entry.") from exc
    return sorted(results, key=lambda item: item.territory_id)


def store_territory_boundary_link(
    link: TerritoryBoundaryLink,
    *,
    directory: Path,
) -> TerritoryBoundaryLink:
    directory.mkdir(parents=True, exist_ok=True)
    document = _read_document(directory)
    links = document["links"]
    assert isinstance(links, dict)
    links[link.territory_id] = {
        key: value for key, value in asdict(link).items() if key != "territory_id"
    }

    target = _links_path(directory)
    temporary = directory / f".{target.name}.{uuid4().hex}.tmp"
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return link
