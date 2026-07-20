from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.leadmap.config import get_settings
from backend.leadmap.geography import BoundaryValidationError, load_boundary_artifact

from .schemas import GeographyArtifactResponse

router = APIRouter(prefix="/api/v1/geography", tags=["geography"])


def get_geographic_artifact_directory() -> Path:
    return Path(get_settings().geographic_artifact_dir)


GeographicArtifactDirectoryDependency = Annotated[
    Path, Depends(get_geographic_artifact_directory)
]


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
