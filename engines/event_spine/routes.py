"""HTTP routes for event_spine (TL-01: durability/replay enforcement).

Provides:
- POST /events/append - append event to spine
- GET /events/replay - cursor-based timeline replay
- GET /events/list - list events with cursor pagination
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from engines.common.identity import (
    RequestContext,
    get_request_context,
    validate_identity_precedence,
)
from engines.common.error_envelope import (
    cursor_invalid_error,
    error_response,
    missing_route_error,
)
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.event_spine.service_reject import EventSpineServiceRejectOnMissing, MissingEventSpineRoute
from engines.event_spine.cloud_event_spine_store import SpineEvent

router = APIRouter(prefix="/events", tags=["event_spine"])


def _ensure_membership(auth, context: RequestContext) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="event_spine",
        )


# ===== Request/Response Models =====

class AppendEventRequest(BaseModel):
    """Request to append event to spine."""
    event_type: str  # analytics|audit|safety|rl|rlha|tuning|budget|strategy_lock|...
    source: str  # ui|agent|connector|tool
    run_id: str  # provenance identifier
    payload: Optional[dict] = None
    user_id: Optional[str] = None
    surface_id: Optional[str] = None
    project_id: Optional[str] = None
    step_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


class SpineEventResponse(BaseModel):
    """Event response (serialized)."""
    event_id: str
    tenant_id: str
    mode: str
    timestamp: str
    event_type: str
    source: str
    run_id: str
    user_id: Optional[str] = None
    surface_id: Optional[str] = None
    project_id: Optional[str] = None
    step_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    payload: dict


class AppendEventResponse(BaseModel):
    """Response to append event."""
    event_id: str
    status: str = "appended"


class ReplayResponse(BaseModel):
    """Timeline replay response."""
    events: List[SpineEventResponse]
    count: int
    cursor: Optional[str] = None  # Last event_id for pagination


# ===== Endpoints =====

@router.post("/append", response_model=AppendEventResponse)
def append_event(
    payload: AppendEventRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """Append event to spine (append-only, routed).
    
    AUTH-01: Enforces server-derived identity. Rejects client-supplied tenant_id/project_id/user_id/surface_id.
    Raises HTTP 403 (auth.identity_override) on mismatch.
    Raises HTTP 503 (event_spine.missing_route) if route missing.
    """
    _ensure_membership(auth, context)
    
    # AUTH-01: Enforce identity precedence
    validate_identity_precedence(
        authenticated_context=context,
        client_supplied_tenant_id=payload.project_id,  # Check if in payload
        client_supplied_project_id=payload.project_id,
        client_supplied_user_id=payload.user_id,
        client_supplied_surface_id=payload.surface_id,
        domain="event_spine",
    )
    
    try:
        svc = EventSpineServiceRejectOnMissing(context)
        event_id = svc.append(
            event_type=payload.event_type,
            source=payload.source,
            run_id=payload.run_id,
            payload=payload.payload,
            user_id=context.user_id,  # Use server-derived identity
            surface_id=context.surface_id,
            project_id=context.project_id,
            step_id=payload.step_id,
            parent_event_id=payload.parent_event_id,
            trace_id=payload.trace_id,
            span_id=payload.span_id,
        )
        return AppendEventResponse(event_id=event_id)
    except MissingEventSpineRoute as e:
        missing_route_error(
            resource_kind="event_spine",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=e.status_code,
        )
    except ValueError as e:
        error_response(
            code="event_spine.invalid_request",
            message=str(e),
            status_code=400,
            resource_kind="event_spine",
            details={"run_id": payload.run_id},
        )
    except Exception as e:
        error_response(
            code="event_spine.append_failed",
            message=f"Append failed: {str(e)}",
            status_code=500,
            resource_kind="event_spine",
            details={"run_id": payload.run_id, "error": str(e)},
        )


@router.get("/replay", response_model=ReplayResponse)
def replay_timeline(
    run_id: str = Query(..., description="Run ID to replay"),
    after_event_id: Optional[str] = Query(None, description="Cursor: only events after this event_id"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=500, description="Max events to return"),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """Cursor-based timeline replay (read-only).
    
    Used to reconstruct timeline across restarts.
    Raises HTTP 503 (event_spine.missing_route) if route missing.
    """
    _ensure_membership(auth, context)
    
    try:
        svc = EventSpineServiceRejectOnMissing(context)
        events = svc.replay(
            run_id=run_id,
            after_event_id=after_event_id,
            event_type=event_type,
            limit=limit,
        )
        
        # Convert to response format
        responses = []
        last_event_id = None
        for event in events:
            responses.append(SpineEventResponse(
                event_id=event.event_id,
                tenant_id=event.tenant_id,
                mode=event.mode,
                timestamp=event.timestamp,
                event_type=event.event_type,
                source=event.source,
                run_id=event.run_id,
                user_id=event.user_id,
                surface_id=event.surface_id,
                project_id=event.project_id,
                step_id=event.step_id,
                parent_event_id=event.parent_event_id,
                trace_id=event.trace_id,
                span_id=event.span_id,
                payload=event.payload,
            ))
            last_event_id = event.event_id
        
        return ReplayResponse(
            events=responses,
            count=len(responses),
            cursor=last_event_id,
        )
    except MissingEventSpineRoute as e:
        missing_route_error(
            resource_kind="event_spine",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=e.status_code,
        )
    except Exception as e:
        message = str(e)
        if after_event_id:
            lower_msg = message.lower()
            if "cursor" in lower_msg or "invalid" in lower_msg:
                cursor_invalid_error(after_event_id, domain="event_spine")
        error_response(
            code="event_spine.replay_failed",
            message=message,
            status_code=500,
            resource_kind="event_spine",
            details={"after_event_id": after_event_id, "run_id": run_id},
        )


@router.get("/list", response_model=ReplayResponse)
def list_events(
    run_id: str = Query(..., description="Run ID to query"),
    after_event_id: Optional[str] = Query(None, description="Cursor: only events after this event_id"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=500, description="Max events to return"),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """List events from spine (same as /replay, convenience alias).
    
    Raises HTTP 503 (event_spine.missing_route) if route missing.
    """
    return replay_timeline(
        run_id=run_id,
        after_event_id=after_event_id,
        event_type=event_type,
        limit=limit,
        context=context,
        auth=auth,
    )
