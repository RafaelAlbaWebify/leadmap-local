from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.models import BusinessRecord, DealRecord

router = APIRouter(prefix="/api/v1", tags=["deals"])
SessionDependency = Annotated[Session, Depends(get_session)]


class DealStage(StrEnum):
    LEAD = "lead"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class DealCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    stage: DealStage = DealStage.LEAD
    value_eur_cents: int | None = Field(default=None, ge=0)
    next_action: str | None = Field(default=None, max_length=1000)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Deal title cannot be blank.")
        return normalized

    @field_validator("next_action")
    @classmethod
    def normalize_next_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DealResponse(BaseModel):
    id: str
    business_id: str
    business_name: str
    title: str
    stage: DealStage
    value_eur_cents: int | None
    next_action: str | None
    created_at: datetime
    updated_at: datetime


def _response(record: DealRecord) -> DealResponse:
    return DealResponse(
        id=record.id,
        business_id=record.business_id,
        business_name=record.business.canonical_name,
        title=record.title,
        stage=DealStage(record.stage),
        value_eur_cents=record.value_eur_cents,
        next_action=record.next_action,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/deals", response_model=list[DealResponse])
def list_deals(session: SessionDependency) -> list[DealResponse]:
    records = session.scalars(
        select(DealRecord)
        .options(joinedload(DealRecord.business))
        .order_by(DealRecord.updated_at.desc(), DealRecord.id)
    ).all()
    return [_response(record) for record in records]


@router.post(
    "/businesses/{business_id}/deals",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_deal(
    business_id: str,
    payload: DealCreate,
    session: SessionDependency,
) -> DealResponse:
    business = session.get(BusinessRecord, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    if business.qualification_status != "qualified":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only qualified businesses can create deals.",
        )

    now = datetime.now(UTC)
    record = DealRecord(
        business=business,
        title=payload.title,
        stage=payload.stage.value,
        value_eur_cents=payload.value_eur_cents,
        next_action=payload.next_action,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _response(record)
