from __future__ import annotations

import os
from typing import Optional

from engines.media_v2.service import get_media_service, MediaService
from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
)
from engines.video_regions.backend import (
    VideoRegionBackend,
    StubRegionsBackend,
    CpuFaceRegionsBackend,
)


class VideoRegionsService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.backend: VideoRegionBackend = self._load_backend()

    def _load_backend(self) -> VideoRegionBackend:
        backend_type = os.getenv("VIDEO_REGION_BACKEND", "stub")
        if backend_type == "cpu_face":
            return CpuFaceRegionsBackend()
        return StubRegionsBackend()

    def analyze_regions(self, req: AnalyzeRegionsRequest) -> AnalyzeRegionsResult:
        asset = self.media_service.get_asset(req.asset_id)
        if not asset:
            raise ValueError(f"Asset {req.asset_id} not found")

        return self.backend.analyze(asset, req, self.media_service)

    def get_analysis(self, artifact_id: str) -> Optional[RegionAnalysisSummary]:
        artifact = self.media_service.get_artifact(artifact_id)
        if not artifact or artifact.kind != "video_region_summary":
            return None
        
        # Read JSON from uri
        try:
            with open(artifact.uri, "r") as f:
                data = f.read()
                return RegionAnalysisSummary.model_validate_json(data)
        except Exception:
            return None

_default_service: Optional[VideoRegionsService] = None

def get_video_regions_service() -> VideoRegionsService:
    global _default_service
    if _default_service is None:
        _default_service = VideoRegionsService()
    return _default_service
