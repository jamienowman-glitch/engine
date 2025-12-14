from typing import List, Optional

from fastapi import APIRouter, HTTPException

from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
)
from engines.video_regions.service import get_video_regions_service

router = APIRouter(prefix="/video/regions", tags=["video_regions"])


@router.post("/analyze", response_model=AnalyzeRegionsResult)
def analyze_regions(req: AnalyzeRegionsRequest):
    service = get_video_regions_service()
    try:
        return service.analyze_regions(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{artifact_id}", response_model=RegionAnalysisSummary)
def get_analysis_summary(artifact_id: str):
    service = get_video_regions_service()
    summary = service.get_analysis(artifact_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
