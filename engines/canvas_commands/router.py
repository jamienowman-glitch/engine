from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response, cursor_invalid_error
from engines.identity.auth import AuthContext, get_auth_context
from engines.canvas_commands.models import CommandEnvelope, RevisionResult, CanvasSnapshot, CanvasReplayEvent
from engines.canvas_commands.service import (
    apply_command, 
    get_canvas_snapshot,
    get_canvas_replay,
)

router = APIRouter(prefix="/canvas", tags=["canvas-commands"])


@router.post("/{canvas_id}/commands", response_model=RevisionResult)
async def post_command(
    canvas_id: str,
    cmd: CommandEnvelope,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """POST /canvas/{canvas_id}/commands - Durable canvas command execution.
    
    Authoritative endpoint per EN-03.
    Requirements:
    - Routing-backed persistence (canvas_command_store)
    - Idempotency via idempotency_key
    - Optimistic concurrency via base_rev
    - Conflicts return recovery_ops
    - GateChain enforced with action=canvas_command
    - Emits canvas_command_committed to event_spine
    """
    # 1. Tenant Check
    if auth_context.default_tenant_id != request_context.tenant_id:
        error_response(
            code="tenant_mismatch",
            message="Tenant ID mismatch",
            status_code=403,
        )
        
    # Ensure canvas_id matches
    if cmd.canvas_id != canvas_id:
        error_response(
            code="canvas_id_mismatch",
            message="Canvas ID in path does not match command envelope",
            status_code=400,
            resource_kind="canvas",
        )
        
    # 2. Service Call
    try:
        result = await apply_command(
            tenant_id=request_context.tenant_id,
            user_id=auth_context.user_id,
            command=cmd,
            context=request_context,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        error_response(
            code="canvas_command_error",
            message=str(e),
            status_code=500,
            resource_kind="canvas",
        )


@router.get("/{canvas_id}/snapshot", response_model=CanvasSnapshot)
async def get_snapshot(
    canvas_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """GET /canvas/{canvas_id}/snapshot - Retrieve canvas head state and revision.
    
    Per EN-04. Returns authoritative state reconstructed from durable timeline.
    """
    if auth_context.default_tenant_id != request_context.tenant_id:
        error_response(
            code="tenant_mismatch",
            message="Tenant ID mismatch",
            status_code=403,
        )
    
    try:
        snapshot = await get_canvas_snapshot(
            canvas_id=canvas_id,
            tenant_id=request_context.tenant_id,
            context=request_context,
        )
        return snapshot
    except HTTPException as e:
        raise e
    except Exception as e:
        error_response(
            code="snapshot_error",
            message=str(e),
            status_code=500,
            resource_kind="canvas",
        )


@router.get("/{canvas_id}/replay")
async def get_replay(
    canvas_id: str,
    after_event_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """GET /canvas/{canvas_id}/replay?after_event_id=... - Replay timeline events.
    
    Per EN-04. Replay durable timeline, works across restarts.
    Returns 410 Gone if cursor is invalid/expired.
    """
    if auth_context.default_tenant_id != request_context.tenant_id:
        error_response(
            code="tenant_mismatch",
            message="Tenant ID mismatch",
            status_code=403,
        )
    
    try:
        events = await get_canvas_replay(
            canvas_id=canvas_id,
            tenant_id=request_context.tenant_id,
            after_event_id=after_event_id,
            context=request_context,
        )
        return {"events": events}
    except Exception as e:
        if "cursor" in str(e).lower() or "invalid" in str(e).lower():
            cursor_invalid_error(after_event_id or "unknown", domain="canvas")
        error_response(
            code="replay_error",
            message=str(e),
            status_code=500,
            resource_kind="canvas",
        )
