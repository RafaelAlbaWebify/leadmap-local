import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.leadmap.domain.enums import QualificationStatus
from backend.leadmap.domain.freshness import calculate_freshness
from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.models import (
    BusinessNoteRecord,
    BusinessRecord,
    ObservationRecord,
)
from backend.leadmap.persistence.repositories import LeadRepository

router = APIRouter(prefix="/api/v1/businesses", tags=["businesses"])
SessionDependency = Annotated[Session, Depends(get_session)]
MAX_NOTE_LENGTH = 4000


class BusinessObservationResponse(BaseModel):
    id: str
    location_id: str
    provider: str
    provider_key: str
    displayed_name: str
    category: str
    source_url: str | None
    observed_at: datetime
    query_text: str
    search_run_status: str
    query_sequence: int | None
    result_rank: int | None
    first_seen_scroll_step: int | None
    candidate_id: str | None
    raw_evidence: str | None
    address_text: str | None


class BusinessLocationResponse(BaseModel):
    id: str
    locality: str
    administrative_area: str | None
    country_code: str
    postal_area: str | None
    phone: str | None
    website: str | None
    latitude: str | None
    longitude: str | None
    created_at: datetime
    updated_at: datetime


class BusinessDetailResponse(BaseModel):
    id: str
    canonical_name: str
    normalized_name: str
    qualification_status: str
    freshness: str
    created_at: datetime
    updated_at: datetime
    locations: list[BusinessLocationResponse]
    observations: list[BusinessObservationResponse]


class BusinessQualificationUpdate(BaseModel):
    qualification_status: QualificationStatus


class BusinessQualificationResponse(BaseModel):
    id: str
    qualification_status: QualificationStatus
    updated_at: datetime


class BusinessNoteCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note content must not be blank.")
        if len(normalized) > MAX_NOTE_LENGTH:
            raise ValueError(f"Note content must be {MAX_NOTE_LENGTH} characters or fewer.")
        return normalized


class BusinessNoteResponse(BaseModel):
    id: str
    business_id: str
    content: str
    created_at: datetime


def _raw_payload(observation: ObservationRecord) -> dict[str, Any]:
    if not observation.raw_payload_json:
        return {}
    try:
        payload = json.loads(observation.raw_payload_json)
    except (json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_text(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _business_detail_response(business: BusinessRecord) -> BusinessDetailResponse:
    observations = sorted(
        (observation for location in business.locations for observation in location.observations),
        key=lambda item: item.observed_at,
        reverse=True,
    )
    latest_observed_at = observations[0].observed_at if observations else None

    return BusinessDetailResponse(
        id=business.id,
        canonical_name=business.canonical_name,
        normalized_name=business.normalized_name,
        qualification_status=business.qualification_status,
        freshness=calculate_freshness(latest_observed_at).value,
        created_at=business.created_at,
        updated_at=business.updated_at,
        locations=[
            BusinessLocationResponse(
                id=location.id,
                locality=location.locality,
                administrative_area=location.administrative_area,
                country_code=location.country_code,
                postal_area=location.postal_area,
                phone=location.phone,
                website=location.website,
                latitude=location.latitude,
                longitude=location.longitude,
                created_at=location.created_at,
                updated_at=location.updated_at,
            )
            for location in business.locations
        ],
        observations=[
            BusinessObservationResponse(
                id=observation.id,
                location_id=observation.location_id,
                provider=observation.provider,
                provider_key=observation.provider_key,
                displayed_name=observation.displayed_name,
                category=observation.category,
                source_url=observation.source_url,
                observed_at=observation.observed_at,
                query_text=observation.search_run.query_text,
                search_run_status=observation.search_run.status,
                query_sequence=_optional_int(_raw_payload(observation), "query_sequence"),
                result_rank=_optional_int(_raw_payload(observation), "result_rank"),
                first_seen_scroll_step=_optional_int(
                    _raw_payload(observation), "first_seen_scroll_step"
                ),
                candidate_id=_optional_text(_raw_payload(observation), "candidate_id"),
                raw_evidence=_optional_text(_raw_payload(observation), "raw_evidence"),
                address_text=_optional_text(_raw_payload(observation), "address_text"),
            )
            for observation in observations
        ],
    )


def _note_response(note: BusinessNoteRecord) -> BusinessNoteResponse:
    return BusinessNoteResponse(
        id=note.id,
        business_id=note.business_id,
        content=note.content,
        created_at=note.created_at,
    )


@router.get("/{business_id}", response_model=BusinessDetailResponse)
def get_business_detail(business_id: str, session: SessionDependency) -> BusinessDetailResponse:
    business = LeadRepository(session).get_business(business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    return _business_detail_response(business)


@router.patch("/{business_id}/qualification", response_model=BusinessQualificationResponse)
def update_business_qualification(
    business_id: str,
    payload: BusinessQualificationUpdate,
    session: SessionDependency,
) -> BusinessQualificationResponse:
    business = session.get(BusinessRecord, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

    business.qualification_status = payload.qualification_status.value
    business.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(business)
    return BusinessQualificationResponse(
        id=business.id,
        qualification_status=payload.qualification_status,
        updated_at=business.updated_at,
    )


@router.get("/{business_id}/notes", response_model=list[BusinessNoteResponse])
def list_business_notes(
    business_id: str,
    session: SessionDependency,
) -> list[BusinessNoteResponse]:
    if session.get(BusinessRecord, business_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

    notes = session.scalars(
        select(BusinessNoteRecord)
        .where(BusinessNoteRecord.business_id == business_id)
        .order_by(BusinessNoteRecord.created_at.desc(), BusinessNoteRecord.id.desc())
    )
    return [_note_response(note) for note in notes]


@router.post(
    "/{business_id}/notes",
    response_model=BusinessNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_business_note(
    business_id: str,
    payload: BusinessNoteCreate,
    session: SessionDependency,
) -> BusinessNoteResponse:
    business = session.get(BusinessRecord, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

    note = BusinessNoteRecord(
        business_id=business.id,
        content=payload.content,
        created_at=datetime.now(UTC),
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return _note_response(note)
