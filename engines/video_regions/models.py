from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _uuid() -> str:
    return uuid.uuid4().hex


RegionType = Literal["face", "teeth", "skin", "eyes", "background", "other"]


class RegionMaskEntry(BaseModel):
    time_ms: int
    region: RegionType
    mask_artifact_id: str  # Reference to a mask artifact (image)
    meta: Dict[str, Any] = Field(default_factory=dict)


class RegionAnalysisSummary(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    asset_id: str
    entries: List[RegionMaskEntry] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
class AnalyzeRegionsRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    include_regions: Optional[List[RegionType]] = None

class AnalyzeRegionsResult(BaseModel):
    summary_artifact_id: str
    summary: RegionAnalysisSummary
