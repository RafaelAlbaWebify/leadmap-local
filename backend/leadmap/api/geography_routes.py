from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.leadmap.config import get_settings
from backend.leadmap.geography import (
    BoundaryValidationError,
    TerritoryBoundaryLink,
    list_boundary_artifacts,
    list_territory_boundary_links,
    load_boundary_artifact,
    store_territory_boundary_link,
)
from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.repositories import LeadRepository

from .schemas import (
    GeographyArtifactResponse,
    GeographyArtifactSummaryResponse,
    TerritoryBoundaryLinkCreate,
    TerritoryBoundaryLinkResponse,
)

router = APIRouter(prefix="/api/v1/geography", tags=["geography"])


def get_geographic_artifact_directory() -> Path:
    return Path(get_settings().geographic_artifact_dir)


GeographicArtifactDirectoryDependency = Annotated[Path, Depends(get_geographic_artifact_directory)]
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/artifacts", response_model=list[GeographyArtifactSummaryResponse])
def get_geographic_artifact_catalog(
    directory: GeographicArtifactDirectoryDependency,
) -> list[GeographyArtifactSummaryResponse]:
    try:
        artifacts = list_boundary_artifacts(directory=directory)
    except BoundaryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return [GeographyArtifactSummaryResponse.model_validate(item) for item in artifacts]


@router.get(
    "/artifacts/{checksum_sha256}",
    response_model=GeographyArtifactResponse,
)
def get_geographic_artifact(
    checksum_sha256: str,
    directory: GeographicArtifactDirectoryDependency,
) -> GeographyArtifactResponse:
    try:
        document = load_boundary_artifact(
            directory=directory,
            checksum_sha256=checksum_sha256,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geographic artifact not found.",
        ) from exc
    except BoundaryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return GeographyArtifactResponse.model_validate(document)


@router.get("/territory-links", response_model=list[TerritoryBoundaryLinkResponse])
def get_territory_boundary_links(
    directory: GeographicArtifactDirectoryDependency,
) -> list[TerritoryBoundaryLinkResponse]:
    try:
        links = list_territory_boundary_links(directory=directory)
    except BoundaryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return [
        TerritoryBoundaryLinkResponse.model_validate(link, from_attributes=True)
        for link in links
    ]


@router.put(
    "/territory-links/{territory_id}",
    response_model=TerritoryBoundaryLinkResponse,
)
def put_territory_boundary_link(
    territory_id: str,
    payload: TerritoryBoundaryLinkCreate,
    directory: GeographicArtifactDirectoryDependency,
    session: SessionDependency,
) -> TerritoryBoundaryLinkResponse:
    if LeadRepository(session).get_territory(territory_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found.")

    try:
        document = load_boundary_artifact(
            directory=directory,
            checksum_sha256=payload.checksum_sha256,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geographic artifact not found.",
        ) from exc
    except BoundaryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    boundaries = document.get("boundaries")
    boundary = (
        next(
            (
                item
                for item in boundaries
                if isinstance(item, dict)
                and item.get("external_id") == payload.boundary_external_id
            ),
            None,
        )
        if isinstance(boundaries, list)
        else None
    )
    if boundary is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Boundary does not exist in the selected geographic artifact.",
        )

    link = TerritoryBoundaryLink(
        territory_id=territory_id,
        checksum_sha256=payload.checksum_sha256,
        boundary_external_id=payload.boundary_external_id,
        boundary_name=str(boundary["name"]),
    )
    try:
        stored = store_territory_boundary_link(link, directory=directory)
    except BoundaryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return TerritoryBoundaryLinkResponse.model_validate(stored, from_attributes=True)
