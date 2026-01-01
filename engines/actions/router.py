from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext, get_request_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain

router = APIRouter(prefix="/actions", tags=["actions"])


class ActionRequest(BaseModel):
    action_name: str
    subject_type: str
    subject_id: str
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/execute")
def execute_action(
    request: ActionRequest,
    context: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    if not request.subject_id:
        raise HTTPException(status_code=400, detail="subject_id is required")
    if not request.action_name:
        raise HTTPException(status_code=400, detail="action_name is required")
    if not request.subject_type:
        raise HTTPException(status_code=400, detail="subject_type is required")

    surface = request.surface_id or context.surface_id or "unknown"
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

    return {
        "status": "PASS",
        "action_name": request.action_name,
        "subject_type": request.subject_type,
        "subject_id": request.subject_id,
    }
