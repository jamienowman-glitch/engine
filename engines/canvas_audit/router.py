from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.canvas_audit.models import AuditRequest, AuditReport
from engines.canvas_audit.service import run_audit

router = APIRouter(prefix="/canvas", tags=["canvas-audit"])

@router.post("/{canvas_id}/audits", response_model=AuditReport)
async def trigger_audit(
    canvas_id: str,
    payload: AuditRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    # 1. Auth Check
    if auth_context.default_tenant_id != request_context.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    return await run_audit(
        canvas_id=canvas_id,
        request=payload,
        user_id=auth_context.user_id,
        tenant_id=request_context.tenant_id
    )
