from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.leadmap.config import get_settings
from backend.leadmap.market_indicators import (
    MarketIndicatorValidationError,
    list_market_indicator_artifacts,
    load_market_indicator_artifact,
    territory_indicator_values,
)


class MarketIndicatorSourceResponse(BaseModel):
    dataset_title: str
    publisher: str
    source_url: str
    licence: str
    published_at: str
    retrieved_at: str


class MarketIndicatorArtifactSummaryResponse(BaseModel):
    schema_version: str
    checksum_sha256: str
    source: MarketIndicatorSourceResponse
    record_count: int


class MarketIndicatorValueResponse(BaseModel):
    territory_key: str
    sector_key: str
    indicator_key: str
    unit: str
    value: float
    notes: str | None
    checksum_sha256: str
    source: MarketIndicatorSourceResponse


router = APIRouter(prefix="/api/v1/market-indicators", tags=["market-indicators"])


def get_market_indicator_directory() -> Path:
    return Path(get_settings().market_indicator_artifact_dir)


MarketIndicatorDirectoryDependency = Annotated[Path, Depends(get_market_indicator_directory)]


def _load(checksum_sha256: str, directory: Path) -> dict[str, object]:
    try:
        return load_market_indicator_artifact(directory, checksum_sha256)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market indicator artifact not found.") from exc
    except (MarketIndicatorValidationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("/artifacts", response_model=list[MarketIndicatorArtifactSummaryResponse])
def get_market_indicator_catalog(
    directory: MarketIndicatorDirectoryDependency,
) -> list[MarketIndicatorArtifactSummaryResponse]:
    try:
        artifacts = list_market_indicator_artifacts(directory)
    except (MarketIndicatorValidationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return [MarketIndicatorArtifactSummaryResponse.model_validate(item) for item in artifacts]


@router.get(
    "/artifacts/{checksum_sha256}/territories/{territory_key}",
    response_model=list[MarketIndicatorValueResponse],
)
def get_territory_market_indicators(
    checksum_sha256: str,
    territory_key: str,
    directory: MarketIndicatorDirectoryDependency,
    sector_key: Annotated[str | None, Query(max_length=200)] = None,
) -> list[MarketIndicatorValueResponse]:
    document = _load(checksum_sha256, directory)
    source = document["source"]
    if not isinstance(source, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Artifact source is invalid.")
    values = territory_indicator_values(document, territory_key=territory_key, sector_key=sector_key)
    response: list[MarketIndicatorValueResponse] = []
    for item in values:
        payload: dict[str, Any] = {
            **item,
            "checksum_sha256": checksum_sha256,
            "source": source,
        }
        response.append(MarketIndicatorValueResponse.model_validate(payload))
    return response
