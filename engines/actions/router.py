from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response, missing_route_error
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain

from engines.event_spine.service_reject import EventSpineServiceRejectOnMissing, MissingEventSpineRoute

router = APIRouter(prefix="/actions", tags=["actions"])


class ActionRequest(BaseModel):
    action_name: str
    subject_type: str
    subject_id: str
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    recommended_canvas_ops: Optional[List[Dict[str, Any]]] = None # Option A: Tool suggests ops


@router.post("/execute")
def execute_action(
    request: ActionRequest,
    context: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    if not request.subject_id:
        error_response(
            code="validation_error",
            message="subject_id is required",
            status_code=400,
            action_name=request.action_name,
        )
    if not request.action_name:
        error_response(
            code="validation_error",
            message="action_name is required",
            status_code=400,
        )
    if not request.subject_type:
        error_response(
            code="validation_error",
            message="subject_type is required",
            status_code=400,
            action_name=request.action_name,
        )

    surface = request.surface_id or context.surface_id or "unknown"
    
    # 1. Enforce GateChain (Blocking)
    try:
        gate_chain.run(
            ctx=context,
            action=request.action_name,
            surface=surface,
            subject_type=request.subject_type,
            subject_id=request.subject_id,
        )
    except HTTPException as exc:
        # Pass through structured gate errors unchanged
        raise exc

    # 2. Emit Tool Completed Event (Option A)
    # We do this AFTER GateChain allows it.
    try:
        spine = EventSpineServiceRejectOnMissing(context)
        
        event_payload = {
            "action_name": request.action_name,
            "subject_type": request.subject_type,
            "subject_id": request.subject_id,
            "payload": request.payload,
        }
        
        if request.recommended_canvas_ops:
            event_payload["recommended_canvas_ops"] = request.recommended_canvas_ops
            
        spine.append(
            event_type="tool_completed",
            source="engines_actions",
            run_id=context.run_id or "unknown",
            payload=event_payload,
            user_id=context.user_id,
            surface_id=surface,
            project_id=context.project_id,
            step_id=context.step_id,
            trace_id=context.trace_id,
        )
    except MissingEventSpineRoute as e:
        missing_route_error(
            resource_kind="event_spine",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=e.status_code,
        )
    except Exception as e:
        # We don't fail the action if emission fails, but we log/warn?
        # Contract says "Events must be written". If spine fails, is it critical?
        # Assuming yes for strict durability.
        # But `EventSpineServiceRejectOnMissing` might just work or raise.
        # Use simple logging for now to not block response if spine is flaky,
        # OR fail strict. "Event Spine Service Reject On Missing" implies strictness.
        # We'll re-raise as 500 if spine is missing/broken.
        error_response(
            code="actions.emit_failed",
            message=f"Failed to emit completion event: {e}",
            status_code=500,
            action_name=request.action_name,
            details={"reason": str(e)},
        )

    return {
        "status": "PASS",
        "action_name": request.action_name,
        "subject_type": request.subject_type,
        "subject_id": request.subject_id,
        "emitted_ops": bool(request.recommended_canvas_ops),
    }
