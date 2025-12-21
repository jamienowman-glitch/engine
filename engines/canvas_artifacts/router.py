from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.canvas_artifacts.models import ArtifactRef
from engines.canvas_artifacts.service import upload_artifact

router = APIRouter(prefix="/canvas", tags=["canvas-artifacts"])

@router.post("/{canvas_id}/artifacts", response_model=ArtifactRef)
async def upload_canvas_artifact(
    canvas_id: str,
    file: UploadFile = File(...),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    if auth_context.default_tenant_id != request_context.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    content = await file.read()
    return await upload_artifact(
        canvas_id=canvas_id,
        data=content,
        mime_type=file.content_type or "application/octet-stream",
        user_id=auth_context.user_id or request_context.user_id or "system",
        tenant_id=request_context.tenant_id,
        env=request_context.env,
    )
