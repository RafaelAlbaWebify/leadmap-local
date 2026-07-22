from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.leadmap.browser import (
    AssistedSession,
    AssistedSessionManager,
    AssistedSessionTransitionError,
    VisibleCaptureUnsupported,
)
from backend.leadmap.config import get_settings

from .routes import get_assisted_session_manager
from .schemas import (
    AssistedSessionReviewResponse,
    CandidateReviewUpdate,
    VisibleCandidateResponse,
)

router = APIRouter(prefix="/api/v1/discovery/session", tags=["assisted discovery"])
ManagerDependency = Annotated[
    AssistedSessionManager,
    Depends(get_assisted_session_manager),
]


def _review_response(session: AssistedSession) -> AssistedSessionReviewResponse:
    candidates = [
        VisibleCandidateResponse.model_validate(candidate) for candidate in session.candidates
    ]
    included_count = sum(candidate.included for candidate in session.candidates)
    return AssistedSessionReviewResponse(
        session_id=session.session_id,
        state=session.state.value,
        territory_id=session.territory_id,
        query_template_id=session.query_template_id,
        start_url=session.start_url,
        error=session.error,
        candidates=candidates,
        included_count=included_count,
        excluded_count=len(candidates) - included_count,
    )


@router.post(
    "/{session_id}/capture-visible",
    response_model=AssistedSessionReviewResponse,
)
def capture_visible_results(
    session_id: str,
    manager: ManagerDependency,
) -> AssistedSessionReviewResponse:
    try:
        session = manager.capture_visible(
            session_id,
            max_results=get_settings().max_capture_results,
        )
    except AssistedSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except VisibleCaptureUnsupported as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Visible-result capture failed: {exc}",
        ) from exc
    return _review_response(session)


@router.patch(
    "/{session_id}/candidates/{candidate_id}",
    response_model=AssistedSessionReviewResponse,
)
def update_candidate_review(
    session_id: str,
    candidate_id: str,
    payload: CandidateReviewUpdate,
    manager: ManagerDependency,
) -> AssistedSessionReviewResponse:
    try:
        session = manager.set_candidate_included(
            session_id,
            candidate_id,
            included=payload.included,
        )
    except AssistedSessionTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _review_response(session)
