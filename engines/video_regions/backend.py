from __future__ import annotations

import os
import tempfile
from typing import Dict, List, Optional, Protocol, Any

from PIL import Image, ImageDraw

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, MediaAsset
from engines.media_v2.service import MediaService
from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
    RegionMaskEntry,
)

class VideoRegionBackend(Protocol):
    def analyze(self, asset: MediaAsset, req: AnalyzeRegionsRequest, media_service: MediaService) -> AnalyzeRegionsResult:
        """
        Analyze the asset and return a detection result.
        Must create necessary artifacts (masks, summary) and return the result object.
        """
        ...

class StubRegionsBackend:
    def _create_dummy_mask(self, tenant_id: str, env: str, user_id: Optional[str], media_service: MediaService) -> str:
        # Create white image (full coverage)
        img = Image.new("L", (512, 512), 255)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            tmp_path = tmp.name

        return tmp_path

    def analyze(self, asset: MediaAsset, req: AnalyzeRegionsRequest, media_service: MediaService) -> AnalyzeRegionsResult:
        # Stub Logic: White square for "face", "teeth", "skin" covering everything.
        dummy_mask_path = self._create_dummy_mask(req.tenant_id, req.env, req.user_id, media_service)
        
        # Register mask artifact
        # Note: We need to upload the file to get a URI or utilize it locally. 
        # For uniformity with "Cpu" backend which might upload detection masks, let's upload/register as typical.
        
        # Actually, let's keep it simple and aligned to previous logic:
        # We register a "mask" artifact.
        
        mask_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="mask",
                uri=dummy_mask_path,
                meta={"region_stub": "v1_white_square"}
            )
        )
        
        entries = []
        regions = req.include_regions or ["face", "teeth", "skin"]
        for region in regions:
            entries.append(
                RegionMaskEntry(
                    time_ms=0,
                    region=region,
                    mask_artifact_id=mask_artifact.id
                )
            )

        summary = RegionAnalysisSummary(
            tenant_id=req.tenant_id,
            env=req.env,
            asset_id=asset.id,
            entries=entries,
            meta={"backend_version": "video_regions_stub_v1"}
        )
        
        return self._save_summary(summary, req, media_service)

    def _save_summary(self, summary: RegionAnalysisSummary, req: AnalyzeRegionsRequest, media_service: MediaService) -> AnalyzeRegionsResult:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            tmp.write(summary.model_dump_json())
            summary_path = tmp.name
            
        summary_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=req.asset_id,
                kind="video_region_summary",
                uri=summary_path,
                meta={"backend_version": summary.meta.get("backend_version")}
            )
        )
        
        return AnalyzeRegionsResult(
            summary_artifact_id=summary_artifact.id,
            summary=summary
        )


class CpuFaceRegionsBackend:
    def analyze(self, asset: MediaAsset, req: AnalyzeRegionsRequest, media_service: MediaService) -> AnalyzeRegionsResult:
        # Simulate face detection:
        # Create a mask that has a white circle in the center (the "face") and black elsewhere.
        # This allows visual verification that blurring only happens on the "face".
        
        img = Image.new("L", (512, 512), 0) # Black background
        draw = ImageDraw.Draw(img)
        # Draw white circle in center
        draw.ellipse((156, 156, 356, 356), fill=255)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            mask_path = tmp.name

        mask_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="mask",
                uri=mask_path,
                meta={"region_stub": "v1_cpu_face_circle"}
            )
        )
        
        # We only really detect "face" here
        entries = []
        # Check if they asked for face
        requested = req.include_regions or ["face"]
        
        if "face" in requested:
            entries.append(
                RegionMaskEntry(
                    time_ms=0,
                    region="face",
                    mask_artifact_id=mask_artifact.id
                )
            )
        
        summary = RegionAnalysisSummary(
            tenant_id=req.tenant_id,
            env=req.env,
            asset_id=asset.id,
            entries=entries,
            meta={"backend_version": "video_regions_cpu_face_v1_stub"}
        )
        
        # Helper to share saving logic? We can duplicate for now or make a mixin. 
        # Duplicating small logic is fine for decoupling.
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            tmp.write(summary.model_dump_json())
            summary_path = tmp.name
            
        summary_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=req.asset_id,
                kind="video_region_summary",
                uri=summary_path,
                meta={"backend_version": "video_regions_cpu_face_v1_stub"}
            )
        )
        
        return AnalyzeRegionsResult(
            summary_artifact_id=summary_artifact.id,
            summary=summary
        )
