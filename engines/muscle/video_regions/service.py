from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from engines.common.identity import RequestContext
from engines.media_v2.service import get_media_service, MediaService
from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
)
from engines.video_regions.backend import (
    CpuFaceRegionsBackend,
    MissingDependencyError,
    OpenCvRegionsBackend,
    RealRegionsBackend,
    StubRegionsBackend,
    VideoRegionBackend,
)


class VideoRegionsService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.backend: VideoRegionBackend = self._load_backend()
        self.stub_backend = StubRegionsBackend()

    def _load_backend(self) -> VideoRegionBackend:
        backend_type = os.getenv("VIDEO_REGION_BACKEND", "real")
        if backend_type == "cpu_face":
            return CpuFaceRegionsBackend()
        if backend_type == "stub":
            return StubRegionsBackend()
        if backend_type == "opencv":
            return OpenCvRegionsBackend()
        return RealRegionsBackend()

    def analyze_regions(
        self, req: AnalyzeRegionsRequest, context: Optional[RequestContext] = None
    ) -> AnalyzeRegionsResult:
        self._validate_tenant_env(req, context)
        asset = self.media_service.get_asset(req.asset_id)
        if not asset:
            raise ValueError(f"Asset {req.asset_id} not found")
        if asset.tenant_id != req.tenant_id or asset.env != req.env:
            raise ValueError("Asset tenant/env mismatch")

        cache_key = self._build_cache_key(asset, req)
        cached = self._maybe_cached_summary(asset.id, cache_key, self.backend.backend_version)
        if cached:
            return cached

        try:
            return self.backend.analyze(asset, req, self.media_service, cache_key=cache_key)
        except MissingDependencyError:
            return self.stub_backend.analyze(asset, req, self.media_service, cache_key=cache_key)

    def get_analysis(
        self, artifact_id: str, context: Optional[RequestContext] = None
    ) -> Optional[RegionAnalysisSummary]:
        artifact = self.media_service.get_artifact(artifact_id)
        if not artifact or artifact.kind != "video_region_summary":
            return None
        if context and (artifact.tenant_id != context.tenant_id or artifact.env != context.env):
            raise ValueError("artifact tenant/env mismatch")
        return self._load_summary_from_uri(artifact.uri)

    def _build_cache_key(self, asset: MediaAsset, req: AnalyzeRegionsRequest) -> str:
        regions = ",".join(sorted(req.include_regions or ["face"]))
        return f"{asset.id}|{self.backend.backend_version}|{regions}"

    def _maybe_cached_summary(
        self, asset_id: str, cache_key: str, backend_version: str
    ) -> Optional[AnalyzeRegionsResult]:
        artifacts = self.media_service.list_artifacts_for_asset(asset_id)
        for art in artifacts:
            if art.kind != "video_region_summary":
                continue
            if art.meta.get("cache_key") != cache_key:
                continue
            if art.meta.get("backend_version") != backend_version:
                continue
            summary = self._load_summary_from_uri(art.uri)
            if summary:
                return AnalyzeRegionsResult(summary_artifact_id=art.id, summary=summary)
        return None

    def _load_summary_from_uri(self, uri: str) -> Optional[RegionAnalysisSummary]:
        try:
            path = Path(uri)
            if not path.exists():
                return None
            return RegionAnalysisSummary.model_validate_json(path.read_text())
        except Exception:
            return None

    def _validate_tenant_env(
        self, req: AnalyzeRegionsRequest, context: Optional[RequestContext]
    ) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("valid tenant_id is required")
        if not req.env:
            raise ValueError("env is required")
        if context and (context.tenant_id != req.tenant_id or context.env != req.env):
            raise ValueError("tenant/env mismatch with request context")

_default_service: Optional[VideoRegionsService] = None

def get_video_regions_service() -> VideoRegionsService:
    global _default_service
    if _default_service is None:
        _default_service = VideoRegionsService()
    return _default_service
