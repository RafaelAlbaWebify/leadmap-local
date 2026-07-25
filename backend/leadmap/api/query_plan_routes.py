from __future__ import annotations

import json
from typing import Annotated
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.leadmap.browser import AssistedSessionConflict, AssistedSessionManager
from backend.leadmap.config import get_settings
from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.repositories import LeadRepository
from backend.leadmap.services.query_plans import PreparedQuery, build_prepared_queries

from .routes import get_assisted_session_manager
from .schemas import AssistedSessionResponse

router = APIRouter(prefix="/api/v1/discovery")
SessionDependency = Annotated[Session, Depends(get_session)]
ManagerDependency = Annotated[
    AssistedSessionManager,
    Depends(get_assisted_session_manager),
]


class PreparedDiscoveryPlanCreate(BaseModel):
    territory_id: str
    query_template_id: str
    max_results_per_query: int = Field(default=20, ge=1, le=100)


class PreparedQueryResponse(BaseModel):
    sequence: int
    phrase: str
    query_text: str


class PreparedDiscoveryPlanResponse(BaseModel):
    territory_id: str
    territory_name: str
    country_code: str
    query_template_id: str
    query_template_name: str
    sector: str
    max_results_per_query: int
    total_planned_queries: int
    prepared_queries: list[PreparedQueryResponse]
    mode: str = "assisted"


class PreparedSessionLaunch(PreparedDiscoveryPlanCreate):
    query_sequence: int = Field(default=1, ge=1, le=1000)


def _prepared_plan(
    payload: PreparedDiscoveryPlanCreate,
    repository: LeadRepository,
) -> PreparedDiscoveryPlanResponse:
    settings = get_settings()
    if payload.max_results_per_query > settings.max_capture_results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Maximum results per query is {settings.max_capture_results}.",
        )

    territory = repository.get_territory(payload.territory_id)
    if territory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Territory not found.",
        )

    template = repository.get_query_template(payload.query_template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query template not found.",
        )

    countries = template.countries_csv.split(",")
    if territory.country_code not in countries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Query template is not configured for the selected territory country.",
        )

    phrases: list[str] = json.loads(template.phrases_json)
    prepared = build_prepared_queries(
        phrases=phrases,
        territory_name=territory.name,
        country_code=territory.country_code,
    )
    return PreparedDiscoveryPlanResponse(
        territory_id=territory.id,
        territory_name=territory.name,
        country_code=territory.country_code,
        query_template_id=template.id,
        query_template_name=template.name,
        sector=template.sector,
        max_results_per_query=payload.max_results_per_query,
        total_planned_queries=len(prepared),
        prepared_queries=[_prepared_query_response(item) for item in prepared],
    )


def _prepared_query_response(query: PreparedQuery) -> PreparedQueryResponse:
    return PreparedQueryResponse(
        sequence=query.sequence,
        phrase=query.phrase,
        query_text=query.query_text,
    )


@router.post("/prepared-plan", response_model=PreparedDiscoveryPlanResponse)
def create_prepared_discovery_plan(
    payload: PreparedDiscoveryPlanCreate,
    session: SessionDependency,
) -> PreparedDiscoveryPlanResponse:
    return _prepared_plan(payload, LeadRepository(session))


@router.post(
    "/prepared-session",
    response_model=AssistedSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def launch_prepared_discovery_session(
    payload: PreparedSessionLaunch,
    session: SessionDependency,
    manager: ManagerDependency,
) -> AssistedSessionResponse:
    plan = _prepared_plan(payload, LeadRepository(session))
    if payload.query_sequence > len(plan.prepared_queries):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Query sequence must be between 1 and {len(plan.prepared_queries)}.",
        )
    selected = plan.prepared_queries[payload.query_sequence - 1]
    start_url = f"https://www.google.com/maps/search/{quote_plus(selected.query_text)}"
    try:
        launched = manager.launch(
            territory_id=plan.territory_id,
            query_template_id=plan.query_template_id,
            start_url=start_url,
        )
    except AssistedSessionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Visible browser launch failed: {exc}",
        ) from exc
    return AssistedSessionResponse(
        session_id=launched.session_id,
        state=launched.state.value,
        territory_id=launched.territory_id,
        query_template_id=launched.query_template_id,
        start_url=launched.start_url,
        error=launched.error,
    )
