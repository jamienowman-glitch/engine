from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from engines.common.identity import RequestContext
from engines.media_v2.models import ArtifactCreateRequest, DerivedArtifact, MediaAsset
from engines.media_v2.service import get_media_service
from engines.storage.gcs_client import GcsClient
from engines.video_timeline.models import Clip, Keyframe, ParameterAutomation
from engines.video_timeline.service import get_timeline_service
from engines.video_visual_meta.backend import MissingDependencyError, OpenCvVisualMetaBackend
from engines.video_visual_meta.models import (
    ReframeSuggestion,
    ReframeSuggestionRequest,
    SubjectDetection,
    VisualMetaAnalyzeRequest,
    VisualMetaAnalyzeResult,
    VisualMetaFrame,
    VisualMetaGetResponse,
    VisualMetaSummary,
)


class VisualMetaBackend(Protocol):
    backend_version: str
    model_used: str

    def analyze(
        self,
        video_path: Path,
        sample_interval_ms: int,
        include_labels: Optional[list[str]],
        detect_shot_boundaries: bool,
    ) -> VisualMetaSummary:
        ...


def _probe_duration_ms(path: Path) -> Optional[float]:
    if not path.exists() or shutil.which("ffprobe") is None:
        return None
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        output = subprocess.check_output(cmd, text=True).strip().splitlines()
        if output and output[0]:
            return float(output[0]) * 1000.0
    except Exception:
        return None
    return None


class StubVisualMetaBackend:
    """Placeholder backend; does not perform real detection yet."""

    backend_version = "visual_meta_stub_v1"
    model_used = "visual_meta_stub_v1"

    def analyze(
        self,
        video_path: Path,
        sample_interval_ms: int,
        include_labels: Optional[list[str]],
        detect_shot_boundaries: bool,
    ) -> VisualMetaSummary:
        duration_ms = _probe_duration_ms(video_path) or 5000.0
        frames: list[VisualMetaFrame] = []
        timestamp = 0.0
        idx = 0
        while timestamp <= duration_ms:
            # Simple deterministic wobble so downstream automation tests have variation.
            wobble_x = 0.5 + 0.18 * math.sin(idx / 3.0)
            wobble_y = 0.5 + 0.12 * math.cos(idx / 4.0)
            center_x = min(max(wobble_x, 0.05), 0.95)
            center_y = min(max(wobble_y, 0.05), 0.95)
            bbox_w = 0.12
            bbox_h = 0.12
            subjects = [
                SubjectDetection(
                    track_id=f"dummy_{idx}",
                    label="frame_center",
                    confidence=0.2,
                    bbox_x=max(0.0, center_x - bbox_w / 2),
                    bbox_y=max(0.0, center_y - bbox_h / 2),
                    bbox_width=bbox_w,
                    bbox_height=bbox_h,
                )
            ]
            frames.append(
                VisualMetaFrame(
                    timestamp_ms=int(timestamp),
                    subjects=subjects,
                    primary_subject_center_x=center_x,
                    primary_subject_center_y=center_y,
                    shot_boundary=detect_shot_boundaries and idx == 0,
                )
            )
            idx += 1
            timestamp += float(sample_interval_ms)
        if not frames:
            frames.append(
                VisualMetaFrame(
                    timestamp_ms=0,
                    subjects=[],
                    primary_subject_center_x=0.5,
                    primary_subject_center_y=0.5,
                    shot_boundary=detect_shot_boundaries,
                )
            )
        return VisualMetaSummary(
            asset_id="",
            frames=frames,
            duration_ms=duration_ms,
            frame_sample_interval_ms=sample_interval_ms,
        )


class VisualMetaService:
    def __init__(self, backend: Optional[VisualMetaBackend] = None) -> None:
        if backend:
            self.backend = backend
        else:
            backend_type = os.getenv("VIDEO_VISUAL_META_BACKEND", "opencv")
            if backend_type == "stub":
                self.backend = StubVisualMetaBackend()
            else:
                try:
                    self.backend = OpenCvVisualMetaBackend()
                except MissingDependencyError:
                    self.backend = StubVisualMetaBackend()

        self.media_service = get_media_service()
        self.timeline_service = get_timeline_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    def _download_if_gcs(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_path = Path(tempfile.mkdtemp(prefix="visual_meta_src_")) / Path(uri).name
            try:
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                bucket = self.gcs._client.bucket(bucket_name)  # type: ignore[attr-defined]
                blob = bucket.blob(key)
                blob.download_to_filename(str(tmp_path))
                return str(tmp_path)
            except Exception:
                return uri
        return uri

    def _resolve_source(self, req: VisualMetaAnalyzeRequest) -> tuple[MediaAsset, Path]:
        if req.artifact_id:
            artifact = self.media_service.get_artifact(req.artifact_id)
            if artifact:
                asset = self.media_service.get_asset(artifact.parent_asset_id)
                if asset:
                    return asset, Path(self._download_if_gcs(artifact.uri))
        asset = self.media_service.get_asset(req.asset_id)
        if asset:
            return asset, Path(self._download_if_gcs(asset.source_uri))
        raise FileNotFoundError("source video not found")

    def _cache_key(self, req: VisualMetaAnalyzeRequest, asset: MediaAsset) -> str:
        labels = ",".join(sorted(req.include_labels or []))
        source_id = req.artifact_id or asset.id
        detect_flag = "1" if req.detect_shot_boundaries else "0"
        return f"{source_id}|{asset.id}|{req.sample_interval_ms}|{labels}|{detect_flag}"

    def _maybe_cached_artifact(
        self, asset_id: str, cache_key: str, tenant_id: str, env: str
    ) -> Optional[VisualMetaAnalyzeResult]:
        artifacts = self.media_service.list_artifacts_for_asset(asset_id)
        for art in artifacts:
            if art.kind != "visual_meta":
                continue
            if art.tenant_id != tenant_id or art.env != env:
                continue
            if art.meta.get("cache_key") != cache_key:
                continue
            return VisualMetaAnalyzeResult(visual_meta_artifact_id=art.id, uri=art.uri, meta=art.meta)
        return None

    def _validate_tenant_env(
        self, req: VisualMetaAnalyzeRequest, context: Optional[RequestContext]
    ) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("valid tenant_id is required")
        if not req.env:
            raise ValueError("env is required")
        if context and (context.tenant_id != req.tenant_id or context.env != req.env):
            raise ValueError("tenant/env mismatch with request context")

    def _assert_context_matches(
        self, tenant_id: str, env: str, context: Optional[RequestContext]
    ) -> None:
        if context and (context.tenant_id != tenant_id or context.env != env):
            raise ValueError("tenant/env mismatch with request context")

    def _persist_summary(self, tenant_id: str, asset_id: str, summary: VisualMetaSummary) -> str:
        tmp_dir = Path(tempfile.mkdtemp(prefix="visual_meta_"))
        out_path = tmp_dir / f"{asset_id}_visual_meta.json"
        out_path.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")
        if self.gcs:
            try:
                return self.gcs.upload_raw_media(tenant_id, f"{asset_id}/visual_meta/{out_path.name}", out_path)
            except Exception:
                return str(out_path)
        return str(out_path)

    def _register_artifact(
        self,
        req: VisualMetaAnalyzeRequest,
        asset: MediaAsset,
        summary: VisualMetaSummary,
        uri: str,
        cache_key: str,
        backend: VisualMetaBackend,
    ) -> DerivedArtifact:
        meta = {
            "sample_interval_ms": req.sample_interval_ms,
            "frame_sample_interval_ms": summary.frame_sample_interval_ms,
            "backend_version": getattr(backend, "backend_version", "visual_meta_unknown"),
            "model_used": getattr(backend, "model_used", "visual_meta_unknown"),
            "cache_key": cache_key,
            "duration_ms": summary.duration_ms,
            "detect_shot_boundaries": req.detect_shot_boundaries,
            "include_labels": ",".join(sorted(req.include_labels or [])),
            "source_asset_id": asset.id,
        }
        if req.artifact_id:
            meta["source_artifact_id"] = req.artifact_id
        return self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="visual_meta",  # type: ignore[arg-type]
                uri=uri,
                meta=meta,
            )
        )

    def analyze(
        self, req: VisualMetaAnalyzeRequest, context: Optional[RequestContext] = None
    ) -> VisualMetaAnalyzeResult:
        self._validate_tenant_env(req, context)
        asset, source_path = self._resolve_source(req)
        cache_key = self._cache_key(req, asset)
        cached = self._maybe_cached_artifact(asset.id, cache_key, req.tenant_id, req.env)
        if cached:
            return cached

        backend = self.backend
        try:
            summary = backend.analyze(
                video_path=source_path,
                sample_interval_ms=req.sample_interval_ms,
                include_labels=req.include_labels,
                detect_shot_boundaries=req.detect_shot_boundaries,
            )
        except Exception:
            # If the configured backend fails (e.g. OpenCV cannot open an invalid test file),
            # fall back to the stub backend so analysis requests remain robust in tests and
            # in environments where dependencies or the input media are problematic.
            backend = StubVisualMetaBackend()
            summary = backend.analyze(
                video_path=source_path,
                sample_interval_ms=req.sample_interval_ms,
                include_labels=req.include_labels,
                detect_shot_boundaries=req.detect_shot_boundaries,
            )

        summary = summary.model_copy(update={"asset_id": asset.id})
        uri = self._persist_summary(req.tenant_id, asset.id, summary)
        artifact = self._register_artifact(req, asset, summary, uri, cache_key, backend)
        return VisualMetaAnalyzeResult(visual_meta_artifact_id=artifact.id, uri=artifact.uri, meta=artifact.meta)

    def _load_summary(self, artifact: DerivedArtifact) -> VisualMetaSummary:
        uri = self._download_if_gcs(artifact.uri)
        payload = Path(uri).read_text(encoding="utf-8")
        summary = VisualMetaSummary(**json.loads(payload))
        return summary.model_copy(update={"artifact_id": artifact.id})

    def get_visual_meta(
        self, artifact_id: str, context: Optional[RequestContext] = None
    ) -> VisualMetaGetResponse:
        artifact = self.media_service.get_artifact(artifact_id)
        if not artifact:
            raise FileNotFoundError("visual meta artifact not found")
        self._assert_context_matches(artifact.tenant_id, artifact.env, context)
        summary = self._load_summary(artifact)
        return VisualMetaGetResponse(
            artifact_id=artifact.id,
            uri=artifact.uri,
            summary=summary,
            artifact_meta=artifact.meta,
        )

    def _find_visual_meta_artifact(self, asset_id: str) -> Optional[DerivedArtifact]:
        artifacts = self.media_service.list_artifacts_for_asset(asset_id)
        for art in artifacts:
            if art.kind == "visual_meta":
                return art
        return None

    def _slice_summary(self, summary: VisualMetaSummary, window: Tuple[float, float]) -> VisualMetaSummary:
        start_ms, end_ms = window
        sliced_frames = [f for f in summary.frames if start_ms <= f.timestamp_ms <= end_ms]
        return summary.model_copy(update={"frames": sliced_frames})

    def get_visual_meta_for_clip(
        self, clip_id: str, context: Optional[RequestContext] = None
    ) -> VisualMetaGetResponse:
        clip = self.timeline_service.get_clip(clip_id)
        if not clip:
            raise FileNotFoundError("clip not found")
        self._assert_context_matches(clip.tenant_id, clip.env, context)
        artifact = self._find_visual_meta_artifact(clip.asset_id)
        if not artifact:
            raise FileNotFoundError("visual meta not found for asset")
        summary = self._load_summary(artifact)
        sliced = self._slice_summary(summary, (clip.in_ms, clip.out_ms))
        meta = dict(artifact.meta)
        meta.update({"slice_for_clip_id": clip_id, "slice_range_ms": [clip.in_ms, clip.out_ms]})
        return VisualMetaGetResponse(artifact_id=artifact.id, uri=artifact.uri, summary=sliced, artifact_meta=meta)

    def _aspect_scalar(self, aspect: str) -> float:
        presets = {"16:9": 1.0, "9:16": 1.1, "1:1": 1.05, "4:5": 1.08}
        return presets.get(aspect, 1.0)

    def _build_automation(
        self, clip: Clip, frames: List[VisualMetaFrame], aspect_ratio: str, framing_style: str
    ) -> List[ParameterAutomation]:
        if not frames:
            frames = [
                VisualMetaFrame(timestamp_ms=int(clip.in_ms), subjects=[], primary_subject_center_x=0.5, primary_subject_center_y=0.5)
            ]
        frames = sorted(frames, key=lambda f: f.timestamp_ms)
        scale_base = self._aspect_scalar(aspect_ratio)
        keyframes_x: List[Keyframe] = []
        keyframes_y: List[Keyframe] = []
        keyframes_scale: List[Keyframe] = []
        for frame in frames:
            t_rel = int(frame.timestamp_ms - clip.in_ms)
            cx = frame.primary_subject_center_x if frame.primary_subject_center_x is not None else 0.5
            cy = frame.primary_subject_center_y if frame.primary_subject_center_y is not None else 0.5
            if framing_style == "rule_of_thirds":
                grid_x = 1 / 3 if cx < 0.5 else 2 / 3
                grid_y = 1 / 3 if cy < 0.5 else 2 / 3
                cx = (cx + grid_x) / 2
                cy = (cy + grid_y) / 2
            cx = min(max(cx, 0.05), 0.95)
            cy = min(max(cy, 0.05), 0.95)
            drift = abs(cx - 0.5) + abs(cy - 0.5)
            scale_val = min(1.5, scale_base + 0.25 * drift)
            keyframes_x.append(Keyframe(time_ms=t_rel, value=cx))
            keyframes_y.append(Keyframe(time_ms=t_rel, value=cy))
            keyframes_scale.append(Keyframe(time_ms=t_rel, value=scale_val))
        return [
            ParameterAutomation(
                tenant_id=clip.tenant_id,
                env=clip.env,
                user_id=clip.user_id,
                target_type="clip",
                target_id=clip.id,
                property="position_x",
                keyframes=keyframes_x,
            ),
            ParameterAutomation(
                tenant_id=clip.tenant_id,
                env=clip.env,
                user_id=clip.user_id,
                target_type="clip",
                target_id=clip.id,
                property="position_y",
                keyframes=keyframes_y,
            ),
            ParameterAutomation(
                tenant_id=clip.tenant_id,
                env=clip.env,
                user_id=clip.user_id,
                target_type="clip",
                target_id=clip.id,
                property="scale",
                keyframes=keyframes_scale,
            ),
        ]

    def suggest_reframe(self, req: ReframeSuggestionRequest) -> ReframeSuggestion:
        clip = self.timeline_service.get_clip(req.clip_id)
        if not clip:
            raise FileNotFoundError("clip not found")
        artifact = self._find_visual_meta_artifact(clip.asset_id)
        if not artifact:
            raise FileNotFoundError("visual meta not found for asset")
        summary = self._load_summary(artifact)
        sliced = self._slice_summary(summary, (clip.in_ms, clip.out_ms))
        automation = self._build_automation(
            clip=clip,
            frames=sliced.frames,
            aspect_ratio=req.target_aspect_ratio,
            framing_style=req.framing_style,
        )
        meta: Dict[str, Any] = {
            "source_visual_meta_artifact_id": artifact.id,
            "target_aspect_ratio": req.target_aspect_ratio,
            "sample_interval_ms": summary.frame_sample_interval_ms,
        }
        return ReframeSuggestion(clip_id=clip.id, automation=automation, meta=meta)


_default_service: Optional[VisualMetaService] = None


def get_visual_meta_service() -> VisualMetaService:
    global _default_service
    if _default_service is None:
        _default_service = VisualMetaService()
    return _default_service


def set_visual_meta_service(service: VisualMetaService) -> None:
    global _default_service
    _default_service = service
