from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.repositories import LeadRepository
from backend.leadmap.services.aggregate_persistence import (
    AggregateBusinessInput,
    AggregateIdentityError,
    AggregateObservationInput,
    persist_aggregate_batch,
)

router = APIRouter(prefix="/api/v1/discovery")
SessionDependency = Annotated[Session, Depends(get_session)]


class AggregateObservationSave(BaseModel):
    query_text: str = Field(min_length=1, max_length=500)
    query_sequence: int = Field(ge=1)
    result_rank: int = Field(ge=1)
    first_seen_scroll_step: int = Field(ge=0)
    captured_at: datetime
    source_url: str | None = Field(default=None, max_length=1000)
    raw_evidence: str | None = None
    candidate_id: str = Field(min_length=1, max_length=200)

    @field_validator("query_text", "candidate_id")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()


class AggregateBusinessSave(BaseModel):
    displayed_name: str = Field(min_length=1, max_length=300)
    normalized_name: str = Field(min_length=1, max_length=300)
    category: str | None = Field(default=None, max_length=200)
    address_text: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    latitude: str | None = Field(default=None, max_length=40)
    longitude: str | None = Field(default=None, max_length=40)
    provider_key: str = Field(default="", max_length=500)
    included: bool
    observations: list[AggregateObservationSave] = Field(min_length=1)

    @field_validator("displayed_name", "normalized_name")
    @classmethod
    def strip_business_text(cls, value: str) -> str:
        return value.strip()


class AggregateBatchSave(BaseModel):
    batch_id: str = Field(min_length=1, max_length=200)
    territory_id: str = Field(min_length=1, max_length=36)
    query_template_id: str = Field(min_length=1, max_length=36)
    businesses: list[AggregateBusinessSave] = Field(min_length=1)

    @field_validator("batch_id", "territory_id", "query_template_id")
    @classmethod
    def strip_batch_text(cls, value: str) -> str:
        return value.strip()


class AggregateSaveResponse(BaseModel):
    businesses_created: int
    businesses_matched: int
    observations_created: int
    observations_skipped: int
    businesses_skipped: int


@router.post(
    "/aggregate-businesses",
    response_model=AggregateSaveResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_aggregate_businesses(
    payload: AggregateBatchSave,
    session: SessionDependency,
) -> AggregateSaveResponse:
    repository = LeadRepository(session)
    territory = repository.get_territory(payload.territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territory not found.")
    if repository.get_query_template(payload.query_template_id) is None:
        raise HTTPException(status_code=404, detail="Query template not found.")

    businesses = tuple(
        AggregateBusinessInput(
            displayed_name=item.displayed_name,
            normalized_name=item.normalized_name,
            category=item.category,
            address_text=item.address_text,
            phone=item.phone,
            website=item.website,
            latitude=item.latitude,
            longitude=item.longitude,
            provider_key=item.provider_key,
            included=item.included,
            observations=tuple(
                AggregateObservationInput(**observation.model_dump())
                for observation in item.observations
            ),
        )
        for item in payload.businesses
    )
    try:
        result = persist_aggregate_batch(
            session,
            batch_id=payload.batch_id,
            territory=territory,
            businesses=businesses,
        )
    except AggregateIdentityError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AggregateSaveResponse(
        businesses_created=result.businesses_created,
        businesses_matched=result.businesses_matched,
        observations_created=result.observations_created,
        observations_skipped=result.observations_skipped,
        businesses_skipped=result.businesses_skipped,
    )
