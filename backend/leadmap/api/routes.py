import json
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.leadmap.browser import (
    AssistedSession,
    AssistedSessionConflict,
    AssistedSessionManager,
    AssistedSessionTransitionError,
    SubprocessPlaywrightProvider,
)
from backend.leadmap.config import get_settings
from backend.leadmap.persistence.database import get_session
from backend.leadmap.persistence.repositories import LeadRepository
from backend.leadmap.services.exports import export_csv, export_json
from backend.leadmap.services.seed import seed_ireland

from .schemas import (
    AssistedSessionLaunch,
    AssistedSessionResponse,
    DashboardResponse,
    DiscoveryPlanCreate,
    DiscoveryPlanResponse,
    LeadResponse,
    QueryTemplateCreate,
    QueryTemplateResponse,
    SeedResponse,
    TerritoryCreate,
    TerritoryResponse,
)

router = APIRouter(prefix="/api/v1")
SessionDependency = Annotated[Session, Depends(get_session)]
_ASSISTED_SESSION_MANAGER = AssistedSessionManager(SubprocessPlaywrightProvider())

_NOW = datetime.now(UTC)
_DEMO_LEADS = [
    LeadResponse(
        id="0c74ef92-098d-4a83-b3bc-153753cc8401",
        name="West Coast Accountancy",
        category="Accountant",
        locality="Galway",
        postal_area="H91",
        website="https://example.com",
        phone="+353 91 000 001",
        first_observed_at=_NOW - timedelta(days=38),
        last_observed_at=_NOW - timedelta(days=4),
        freshness="fresh",
        qualification_status="needs_review",
    ),
    LeadResponse(
        id="0c74ef92-098d-4a83-b3bc-153753cc8402",
        name="Harbour Legal",
        category="Solicitor",
        locality="Dublin",
        postal_area="D02",
        website=None,
        phone="+353 1 000 002",
        first_observed_at=_NOW - timedelta(days=50),
        last_observed_at=_NOW - timedelta(days=34),
        freshness="ageing",
        qualification_status="qualified",
    ),
    LeadResponse(
        id="0c74ef92-098d-4a83-b3bc-153753cc8403",
        name="Atlantic Dental Clinic",
        category="Dentist",
        locality="Cork",
        postal_area="T12",
        website="https://example.org",
        phone=None,
        first_observed_at=_NOW - timedelta(days=2),
        last_observed_at=_NOW - timedelta(days=2),
        freshness="never_verified",
        qualification_status="needs_review",
    ),
]


def get_assisted_session_manager() -> AssistedSessionManager:
    return _ASSISTED_SESSION_MANAGER


AssistedSessionManagerDependency = Annotated[
    AssistedSessionManager,
    Depends(get_assisted_session_manager),
]


def _integrity_conflict(exc: IntegrityError, resource: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"{resource} already exists or violates a uniqueness constraint.",
    )


def _lead_responses(repository: LeadRepository, limit: int) -> list[LeadResponse]:
    return [LeadResponse.model_validate(item) for item in repository.recent_leads(limit=limit)]


def _discovery_plan(payload: DiscoveryPlanCreate, repository: LeadRepository) -> DiscoveryPlanResponse:
    settings = get_settings()
    if payload.max_results_per_query > settings.max_capture_results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Maximum results per query is {settings.max_capture_results}.",
        )

    territory = repository.get_territory(payload.territory_id)
    if territory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found.")

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
    return DiscoveryPlanResponse(
        territory_id=territory.id,
        territory_name=territory.name,
        country_code=territory.country_code,
        query_template_id=template.id,
        query_template_name=template.name,
        sector=template.sector,
        phrases=phrases,
        max_results_per_query=payload.max_results_per_query,
        total_planned_queries=len(phrases),
    )


def _session_response(session: AssistedSession) -> AssistedSessionResponse:
    return AssistedSessionResponse(
        session_id=session.session_id,
        state=session.state.value,
        territory_id=session.territory_id,
        query_template_id=session.query_template_id,
        start_url=session.start_url,
        error=session.error,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(session: SessionDependency) -> DashboardResponse:
    repository = LeadRepository(session)
    businesses = repository.list_businesses()
    territories = repository.list_territories()
    if not businesses:
        return DashboardResponse(
            total_businesses=len(_DEMO_LEADS),
            qualified_leads=sum(x.qualification_status == "qualified" for x in _DEMO_LEADS),
            needs_review=sum(x.qualification_status == "needs_review" for x in _DEMO_LEADS),
            stale_records=0,
            territories=max(len(territories), 3),
            recent_leads=_DEMO_LEADS,
        )
    return DashboardResponse(
        total_businesses=len(businesses),
        qualified_leads=sum(x.qualification_status == "qualified" for x in businesses),
        needs_review=sum(x.qualification_status == "needs_review" for x in businesses),
        stale_records=0,
        territories=len(territories),
        recent_leads=_lead_responses(repository, limit=10),
    )


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(session: SessionDependency, limit: int = 250) -> list[LeadResponse]:
    safe_limit = min(max(limit, 1), 1000)
    return _lead_responses(LeadRepository(session), limit=safe_limit)


@router.post("/seed/ireland", response_model=SeedResponse)
def seed_ireland_workspace(session: SessionDependency) -> SeedResponse:
    return SeedResponse.model_validate(seed_ireland(session))


@router.post("/territories", response_model=TerritoryResponse, status_code=status.HTTP_201_CREATED)
def create_territory(payload: TerritoryCreate, session: SessionDependency) -> TerritoryResponse:
    try:
        record = LeadRepository(session).create_territory(**payload.model_dump())
    except IntegrityError as exc:
        session.rollback()
        raise _integrity_conflict(exc, "Territory") from exc
    return TerritoryResponse.model_validate(record, from_attributes=True)


@router.get("/territories", response_model=list[TerritoryResponse])
def list_territories(session: SessionDependency) -> list[TerritoryResponse]:
    records = LeadRepository(session).list_territories()
    return [TerritoryResponse.model_validate(item, from_attributes=True) for item in records]


@router.post(
    "/query-templates", response_model=QueryTemplateResponse, status_code=status.HTTP_201_CREATED
)
def create_query_template(
    payload: QueryTemplateCreate, session: SessionDependency
) -> QueryTemplateResponse:
    try:
        record = LeadRepository(session).create_query_template(**payload.model_dump())
    except IntegrityError as exc:
        session.rollback()
        raise _integrity_conflict(exc, "Query template") from exc
    return QueryTemplateResponse(
        id=record.id,
        name=record.name,
        sector=record.sector,
        countries=record.countries_csv.split(","),
        phrases=json.loads(record.phrases_json),
        created_at=record.created_at,
    )


@router.get("/query-templates", response_model=list[QueryTemplateResponse])
def list_query_templates(
    session: SessionDependency, country_code: str | None = None
) -> list[QueryTemplateResponse]:
    records = LeadRepository(session).list_query_templates(country_code)
    return [
        QueryTemplateResponse(
            id=item.id,
            name=item.name,
            sector=item.sector,
            countries=item.countries_csv.split(","),
            phrases=json.loads(item.phrases_json),
            created_at=item.created_at,
        )
        for item in records
    ]


@router.post("/discovery/plan", response_model=DiscoveryPlanResponse)
def create_discovery_plan(
    payload: DiscoveryPlanCreate, session: SessionDependency
) -> DiscoveryPlanResponse:
    return _discovery_plan(payload, LeadRepository(session))


@router.get("/discovery/session", response_model=AssistedSessionResponse)
def get_discovery_session(manager: AssistedSessionManagerDependency) -> AssistedSessionResponse:
    return _session_response(manager.snapshot())


@router.post(
    "/discovery/session",
    response_model=AssistedSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def launch_discovery_session(
    payload: AssistedSessionLaunch,
    session: SessionDependency,
    manager: AssistedSessionManagerDependency,
) -> AssistedSessionResponse:
    plan = _discovery_plan(payload, LeadRepository(session))
    search_text = f"{plan.phrases[0]} in {plan.territory_name}, {plan.country_code}"
    start_url = f"https://www.google.com/maps/search/{quote_plus(search_text)}"
    try:
        launched = manager.launch(
            territory_id=plan.territory_id,
            query_template_id=plan.query_template_id,
            start_url=start_url,
        )
    except AssistedSessionConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Visible browser launch failed: {exc}",
        ) from exc
    return _session_response(launched)


@router.post(
    "/discovery/session/{session_id}/ready",
    response_model=AssistedSessionResponse,
)
def mark_discovery_session_ready(
    session_id: str,
    manager: AssistedSessionManagerDependency,
) -> AssistedSessionResponse:
    try:
        return _session_response(manager.mark_ready(session_id))
    except AssistedSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete(
    "/discovery/session/{session_id}",
    response_model=AssistedSessionResponse,
)
def stop_discovery_session(
    session_id: str,
    manager: AssistedSessionManagerDependency,
) -> AssistedSessionResponse:
    try:
        return _session_response(manager.stop(session_id))
    except AssistedSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/exports/leads.csv")
def export_leads_csv(session: SessionDependency) -> Response:
    content = export_csv(LeadRepository(session).list_businesses())
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leadmap-leads.csv"'},
    )


@router.get("/exports/leads.json")
def export_leads_json(session: SessionDependency) -> Response:
    content = export_json(LeadRepository(session).list_businesses())
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="leadmap-leads.json"'},
    )
