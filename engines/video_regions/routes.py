from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
)
from engines.video_regions.service import get_video_regions_service

router = APIRouter(prefix="/video/regions", tags=["video_regions"])


def _enforce_regions_guard(
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


@router.post("/analyze", response_model=AnalyzeRegionsResult)
async def analyze_regions(
    req: AnalyzeRegionsRequest,
    context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    service = get_video_regions_service()
    _enforce_regions_guard(
        context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    try:
        return service.analyze_regions(req, context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{artifact_id}", response_model=RegionAnalysisSummary)
async def get_analysis_summary(
    artifact_id: str,
    context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    service = get_video_regions_service()
    _enforce_regions_guard(context, auth_context)
    try:
        summary = service.get_analysis(artifact_id, context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
