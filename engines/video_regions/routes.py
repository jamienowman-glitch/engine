from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
)
from engines.video_regions.service import get_video_regions_service

router = APIRouter(prefix="/video/regions", tags=["video_regions"])


@router.post("/analyze", response_model=AnalyzeRegionsResult)
async def analyze_regions(
    req: AnalyzeRegionsRequest, context: RequestContext = Depends(get_request_context)
):
    service = get_video_regions_service()
    try:
        return service.analyze_regions(req, context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{artifact_id}", response_model=RegionAnalysisSummary)
async def get_analysis_summary(
    artifact_id: str, context: RequestContext = Depends(get_request_context)
):
    service = get_video_regions_service()
    try:
        summary = service.get_analysis(artifact_id, context)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
