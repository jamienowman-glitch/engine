from __future__ import annotations

import hashlib
import os
import random
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from PIL import Image, ImageDraw

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    cv2 = None
    np = None
    HAS_OPENCV = False

from engines.media_v2.models import ArtifactCreateRequest, MediaAsset
from engines.media_v2.service import MediaService
from engines.video_regions.models import (
    AnalyzeRegionsRequest,
    AnalyzeRegionsResult,
    RegionAnalysisSummary,
    RegionMaskEntry,
)


class MissingDependencyError(Exception):
    """Raised when a backend dependency (e.g., OpenCV) is missing."""


def _mask_artifact_path(tenant_id: str, env: str, asset_id: str, artifact_name: str, ext: str = ".png") -> Path:
    # DoD: mask artifacts use enforced prefix: tenants/{tenant}/{env}/media_v2/{asset_id}/regions/
    # We use a base directory that can be mounted or synced. For now, we use a fixed local root
    # similar to how media_v2 might store things locally before GCS upload.
    # We avoid tempfile.gettempdir() to ensure paths are predictable and stable.
    base_root = Path(os.getenv("MEDIA_ARTIFACTS_ROOT", "/tmp/northstar/media_v2"))
    base = base_root / "tenants" / tenant_id / env / asset_id / "regions"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{artifact_name}{ext}"


def _persist_summary_artifact(
    summary: RegionAnalysisSummary,
    req: AnalyzeRegionsRequest,
    media_service: MediaService,
) -> AnalyzeRegionsResult:
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
            meta=summary.meta,
        )
    )
    return AnalyzeRegionsResult(summary_artifact_id=summary_artifact.id, summary=summary)


class VideoRegionBackend(Protocol):
    backend_version: str
    model_used: str

    def analyze(
        self,
        asset: MediaAsset,
        req: AnalyzeRegionsRequest,
        media_service: MediaService,
        cache_key: str,
    ) -> AnalyzeRegionsResult:
        ...


class StubRegionsBackend:
    backend_version = "video_regions_stub_v1"
    model_used = "video_regions_stub_v1"

    def analyze(
        self,
        asset: MediaAsset,
        req: AnalyzeRegionsRequest,
        media_service: MediaService,
        cache_key: str,
    ) -> AnalyzeRegionsResult:
        mask_path = self._create_dummy_mask(req.tenant_id, req.env, asset.id)
        mask_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="mask",
                uri=str(mask_path),
                meta={
                    "backend_version": self.backend_version,
                    "model_used": self.model_used,
                    "cache_key": cache_key,
                },
            )
        )

        regions = req.include_regions or ["face", "teeth", "skin"]
        summary = RegionAnalysisSummary(
            tenant_id=req.tenant_id,
            env=req.env,
            asset_id=asset.id,
            entries=[
                RegionMaskEntry(
                    time_ms=0,
                    region=region,
                    mask_artifact_id=mask_artifact.id,
                    meta={"confidence": 0.1},
                )
                for region in regions
            ],
            meta={
                "backend_version": self.backend_version,
                "model_used": self.model_used,
                "cache_key": cache_key,
                "duration_ms": float(asset.duration_ms or 0.0),
            },
        )
        return _persist_summary_artifact(summary, req, media_service)

    def _create_dummy_mask(self, tenant_id: str, env: str, asset_id: str) -> Path:
        img = Image.new("L", (512, 512), 255)
        draw = ImageDraw.Draw(img)
        draw.rectangle((128, 128, 384, 384), fill=128)
        artifact_id = hashlib.sha256(f"{tenant_id}:{env}:{asset_id}".encode()).hexdigest()[:12]
        path = _mask_artifact_path(tenant_id, env, asset_id, f"stub_mask_{artifact_id}")
        img.convert("RGB").save(path)
        return path


class RealRegionsBackend:
    backend_version = "video_regions_real_v1"
    model_used = "opencv_haar_v1"
    _cascade_name = "haarcascade_frontalface_default.xml"
    _supported_regions = {"face"}

    def __init__(self, min_confidence: Optional[float] = None):
        self.min_confidence = float(min_confidence or os.getenv("VIDEO_REGIONS_MIN_CONFIDENCE", "0.5"))
        self._cascade: Optional[cv2.CascadeClassifier] = None

    def analyze(
        self,
        asset: MediaAsset,
        req: AnalyzeRegionsRequest,
        media_service: MediaService,
        cache_key: str,
    ) -> AnalyzeRegionsResult:
        if not HAS_OPENCV or cv2 is None or np is None:
            raise MissingDependencyError("OpenCV or NumPy is required for RealRegionsBackend")

        include = set(req.include_regions or ["face"])
        if not include & self._supported_regions:
            raise ValueError("Requested regions are not supported by the real detector")

        self._ensure_cascade()
        detections = self._detect_faces(asset.source_uri, include, cache_key)
        mask_path = self._write_mask(asset, req, detections, cache_key)

        mask_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="mask",
                uri=str(mask_path),
                meta={
                    "backend_version": self.backend_version,
                    "model_used": self.model_used,
                    "cache_key": cache_key,
                    "regions": sorted(include),
                    "confidence_avg": sum(d["confidence"] for d in detections) / max(len(detections), 1),
                },
            )
        )

        entries = [
            RegionMaskEntry(
                time_ms=int(d["time_ms"]),
                region="face",
                mask_artifact_id=mask_artifact.id,
                meta={
                    "confidence": d["confidence"],
                    "bbox": d["bbox"],
                },
            )
            for d in detections
        ]

        summary = RegionAnalysisSummary(
            tenant_id=req.tenant_id,
            env=req.env,
            asset_id=asset.id,
            entries=entries,
            meta={
                "backend_version": self.backend_version,
                "model_used": self.model_used,
                "cache_key": cache_key,
                "duration_ms": float(asset.duration_ms or 0.0),
            },
        )
        return _persist_summary_artifact(summary, req, media_service)

    def _ensure_cascade(self) -> None:
        if self._cascade is None:
            cascade_path = Path(cv2.data.haarcascades) / self._cascade_name
            if not cascade_path.exists():
                raise MissingDependencyError("OpenCV Haar cascade not available")
            cascade = cv2.CascadeClassifier(str(cascade_path))
            if cascade.empty():
                raise MissingDependencyError("Failed to load Haar cascade for face detection")
            self._cascade = cascade

    def _detect_faces(self, source_uri: str, include: set[str], cache_key: str) -> List[Dict[str, Any]]:
        cap = cv2.VideoCapture(source_uri)
        if not cap.isOpened():
            cap.release()
            raise ValueError("unable to open video source for face detection")

        detections: List[Dict[str, Any]] = []
        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                return []
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self._cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            rng = self._seed_rng(source_uri, include, cache_key)
            height, width = gray.shape[:2]
            timestamp = int(cap.get(cv2.CAP_PROP_POS_MSEC) or 0)
            for rect in rects:
                if len(rect) != 4:
                    continue
                x, y, w, h = rect
                bbox = (int(x), int(y), int(max(1, w)), int(max(1, h)))
                area_ratio = (bbox[2] * bbox[3]) / max(1.0, width * height)
                confidence = min(0.99, 0.5 + area_ratio * 0.4 + rng.random() * 0.1)
                if confidence < self.min_confidence:
                    continue
                detections.append({
                    "bbox": bbox,
                    "confidence": float(confidence),
                    "time_ms": timestamp,
                })
        finally:
            cap.release()
        return detections

    def _seed_rng(self, source: str, include: set[str], cache_key: str) -> random.Random:
        seed_source = f"{source}:{','.join(sorted(include))}:{cache_key}"
        seed = int(hashlib.sha256(seed_source.encode()).hexdigest(), 16) & 0xFFFFFFFF
        random.seed(seed)
        np.random.seed(seed)
        return random.Random(seed)

    def _write_mask(
        self,
        asset: MediaAsset,
        req: AnalyzeRegionsRequest,
        detections: List[Dict[str, Any]],
        cache_key: str,
    ) -> Path:
        width = int(asset.meta.get("width", 512))
        height = int(asset.meta.get("height", 512))
        mask = np.zeros((height, width, 3), dtype=np.uint8)
        for detection in detections:
            x, y, w, h = detection["bbox"]
            center = (x + w // 2, y + h // 2)
            axes = (max(1, w // 2), max(1, h // 2))
            cv2.ellipse(mask, center, axes, 0, 0, 360, (255, 255, 255), -1)
        img = Image.fromarray(mask)
        artifact_id = hashlib.sha256(f"{asset.id}:{cache_key}".encode()).hexdigest()[:12]
        path = _mask_artifact_path(req.tenant_id, req.env, asset.id, f"real_mask_{artifact_id}")
        img.save(path)
        return path


class CpuFaceRegionsBackend:
    backend_version = "video_regions_cpu_face_v1_stub"
    model_used = "cpu_circle_stub"

    def analyze(
        self,
        asset: MediaAsset,
        req: AnalyzeRegionsRequest,
        media_service: MediaService,
        cache_key: str,
    ) -> AnalyzeRegionsResult:
        img = Image.new("L", (512, 512), 0)
        draw = ImageDraw.Draw(img)
        draw.ellipse((156, 156, 356, 356), fill=255)
        mask_path = _mask_artifact_path(req.tenant_id, req.env, asset.id, f"cpu_face_mask_{hashlib.sha256(asset.id.encode()).hexdigest()[:8]}")
        img.save(mask_path)
        mask_artifact = media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="mask",
                uri=str(mask_path),
                meta={
                    "backend_version": self.backend_version,
                    "model_used": self.model_used,
                    "cache_key": cache_key,
                },
            )
        )
        entries = []
        if "face" in (req.include_regions or ["face"]):
            entries.append(
                RegionMaskEntry(
                    time_ms=0,
                    region="face",
                    mask_artifact_id=mask_artifact.id,
                    meta={"confidence": 0.5},
                )
            )
        summary = RegionAnalysisSummary(
            tenant_id=req.tenant_id,
            env=req.env,
            asset_id=asset.id,
            entries=entries,
            meta={
                "backend_version": self.backend_version,
                "model_used": self.model_used,
                "cache_key": cache_key,
                "duration_ms": float(asset.duration_ms or 0.0),
            },
        )
        return _persist_summary_artifact(summary, req, media_service)


class OpenCvRegionsBackend(RealRegionsBackend):
    backend_version = "video_regions_opencv_v1"
    model_used = "opencv_haar_v1"
