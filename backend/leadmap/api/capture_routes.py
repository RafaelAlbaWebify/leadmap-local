from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.leadmap.browser import (
    AssistedSession,
    AssistedSessionManager,
    AssistedSessionTransitionError,
    TraversalLimits,
    VisibleCaptureUnsupported,
)
from backend.leadmap.config import get_settings

from .routes import get_assisted_session_manager
from .schemas import (
    AssistedSessionReviewResponse,
    CandidateReviewUpdate,
    TraversalProgressResponse,
    TraversalStopReasonValue,
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
    stop_reason = cast(TraversalStopReasonValue | None, session.traversal_stop_reason)
    progress = None
    if (
        session.traversal_query_text is not None
        and session.traversal_query_sequence is not None
        and session.traversal_scroll_step is not None
        and session.traversal_unique_cards is not None
        and session.traversal_stagnant_scrolls is not None
        and session.traversal_elapsed_seconds is not None
    ):
        progress = TraversalProgressResponse(
            query_text=session.traversal_query_text,
            query_sequence=session.traversal_query_sequence,
            scroll_step=session.traversal_scroll_step,
            unique_cards=session.traversal_unique_cards,
            stagnant_scrolls=session.traversal_stagnant_scrolls,
            elapsed_seconds=session.traversal_elapsed_seconds,
            stop_reason=stop_reason,
        )
    return AssistedSessionReviewResponse(
        session_id=session.session_id,
        state=session.state.value,
        territory_id=session.territory_id,
        query_template_id=session.query_template_id,
        start_url=session.start_url,
        error=session.error,
        traversal_progress=progress,
        traversal_stop_reason=stop_reason,
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


@router.post(
    "/{session_id}/collect-bounded",
    response_model=AssistedSessionReviewResponse,
)
def collect_bounded_results(
    session_id: str,
    manager: ManagerDependency,
    query_text: Annotated[str, Query(min_length=1, max_length=500)],
    query_sequence: Annotated[int, Query(ge=1, le=1000)] = 1,
) -> AssistedSessionReviewResponse:
    settings = get_settings()
    limits = TraversalLimits(
        max_cards=settings.max_traversal_results,
        max_scrolls=settings.max_traversal_scrolls,
        max_elapsed_seconds=settings.max_traversal_seconds,
        max_stagnant_scrolls=settings.max_stagnant_scrolls,
    )
    try:
        session = manager.collect_bounded(
            session_id,
            query_text=query_text,
            query_sequence=query_sequence,
            limits=limits,
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
            detail=f"Bounded result collection failed: {exc}",
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
