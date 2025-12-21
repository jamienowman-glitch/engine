from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.canvas_commands.models import CommandEnvelope, RevisionResult
from engines.canvas_commands.service import apply_command

router = APIRouter(prefix="/commands", tags=["canvas-commands"])

@router.post("", response_model=RevisionResult)
async def post_command(
    cmd: CommandEnvelope,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    # 1. Tenant Check
    if auth_context.default_tenant_id != request_context.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
        
    # 2. Service Call
    try:
        result = await apply_command(
            tenant_id=request_context.tenant_id,
            user_id=auth_context.user_id,
            command=cmd
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
