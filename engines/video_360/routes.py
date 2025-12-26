from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.video_360.models import (
    Render360Request,
    Render360Response,
    VirtualCameraPath,
)
from engines.video_360.service import get_video_360_service


def _enforce_video_360_guard(
    request_context: RequestContext,
    auth_context: AuthContext,
    *,
    tenant_id: Optional[str] = None,
    env: Optional[str] = None,
) -> None:
    require_tenant_membership(auth_context, request_context.tenant_id)
    assert_context_matches(
        request_context,
        tenant_id=tenant_id,
        env=env,
        project_id=request_context.project_id,
    )

router = APIRouter(prefix="/video/360", tags=["video_360"])


@router.post("/camera-paths", response_model=VirtualCameraPath)
def create_path(
    path: VirtualCameraPath,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_video_360_guard(
        request_context,
        auth_context,
        tenant_id=path.tenant_id,
        env=path.env,
    )
    service = get_video_360_service()
    return service.create_path(path)


@router.get("/camera-paths/{path_id}", response_model=VirtualCameraPath)
def get_path(
    path_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_video_360_guard(request_context, auth_context)
    service = get_video_360_service()
    path = service.get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
    return path


@router.get("/camera-paths", response_model=List[VirtualCameraPath])
def list_paths(
    tenant_id: str,
    asset_id: Optional[str] = None,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_video_360_guard(request_context, auth_context, tenant_id=tenant_id)
    service = get_video_360_service()
    return service.list_paths(tenant_id, asset_id)


@router.post("/render", response_model=Render360Response)
def render_360(
    req: Render360Request,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_video_360_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    service = get_video_360_service()
    try:
        return service.render_360_to_flat(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch-all for ffmpeg errors or other issues
        raise HTTPException(status_code=500, detail=str(e))
