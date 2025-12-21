from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from engines.audio_shared.health import (
    build_backend_health_meta,
    check_dependencies,
    DependencyInfo,
    DependencyMissingError,
    prepare_local_asset,
)
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.media_v2.service import MediaService, get_media_service
from engines.audio_resample.models import ResampleRequest, ResampleResult
from engines.storage.gcs_client import GcsClient

QUALITY_PRESET_ARGS = {
    "draft": ["-resampler", "soxr", "-precision", "12"],
    "quality": ["-resampler", "soxr", "-precision", "28"]
}
DEFAULT_QUALITY_PRESET = "quality"


def _normalize_quality_preset(preset: Optional[str]) -> str:
    if not preset:
        return DEFAULT_QUALITY_PRESET
    normalized = preset.lower()
    if normalized in {"quality", "high"}:
        return "quality"
    if normalized == "draft":
        return "draft"
    return DEFAULT_QUALITY_PRESET


def _quality_command_args(preset: str) -> List[str]:
    return QUALITY_PRESET_ARGS.get(_normalize_quality_preset(preset), [])

logger = logging.getLogger(__name__)
MIN_TEMPO_SCALE = 0.5
MAX_TEMPO_SCALE = 2.0
MAX_PITCH_SEMITONES = 12.0


class AudioResampleService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self._temp_files: List[Path] = []

    def _ensure_local(self, uri: str) -> str:
        try:
            local_path, is_temp = prepare_local_asset(uri, self.gcs)
            if is_temp:
                self._temp_files.append(Path(local_path))
            return local_path
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", uri, exc)
            raise

    def _cleanup_temp_files(self) -> None:
        while self._temp_files:
            path = self._temp_files.pop()
            try:
                if path.exists():
                    path.unlink()
            except Exception as exc:
                logger.debug("Failed to cleanup temp file %s: %s", path, exc)

    @staticmethod
    def _validate_context(req: ResampleRequest) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("Invalid tenant_id")
        if not req.env:
            raise ValueError("Invalid env")

    def _ensure_ffmpeg(self) -> Dict[str, DependencyInfo]:
        deps = check_dependencies()
        ffmpeg_info = deps.get("ffmpeg")
        if not ffmpeg_info or not ffmpeg_info.available:
            reason = ffmpeg_info.error if ffmpeg_info else "ffmpeg missing"
            details = {
                "code": "missing_dependency",
                "service": "audio_resample",
                "dependency": "ffmpeg",
                "required_version": "6.0",
                "reason": reason,
                "backend_version": None,
            }
            logger.error("FFmpeg unavailable for resample: %s", details)
            raise DependencyMissingError(details)
        return deps

    def resample_artifact(self, req: ResampleRequest) -> ResampleResult:
        self._validate_context(req)
        deps = self._ensure_ffmpeg()
        backend_meta = build_backend_health_meta(
            service_name="audio_resample",
            backend_type="ffmpeg",
            primary_dependency="ffmpeg",
            dependencies=deps,
        )

        art = self.media_service.get_artifact(req.artifact_id)
        if not art:
            raise ValueError(f"Artifact not found: {req.artifact_id}")

        source_uri = art.uri
        local_in = self._ensure_local(source_uri)
        try:
            source_bpm = req.input_bpm or art.meta.get("bpm")
            tempo_scale = None
            if req.target_bpm and source_bpm:
                ratio = req.target_bpm / float(source_bpm)
                tempo_scale = max(MIN_TEMPO_SCALE, min(ratio, MAX_TEMPO_SCALE))

            pitch = max(-MAX_PITCH_SEMITONES, min(req.pitch_semitones, MAX_PITCH_SEMITONES))

            extras = []
            applied_params: Dict[str, Any] = {}
            quality_preset = _normalize_quality_preset(req.quality_preset)
            applied_params["quality_preset"] = quality_preset

            if tempo_scale:
                extras.append(f"tempo={tempo_scale:.3f}")
                applied_params["tempo_scale"] = tempo_scale

            if pitch != 0.0:
                extras.append(f"pitch={pitch}")
                applied_params["pitch_semitones"] = pitch

            if not extras:
                reason = "no tempo or pitch changes requested"
                logger.warning(
                    "No resampling applied for %s (%s)", art.id, reason
                )
                return ResampleResult(
                    artifact_id=art.id,
                    uri=art.uri,
                    duration_ms=art.end_ms - art.start_ms if art.end_ms else 0.0,
                    meta={
                        "backend_info": backend_meta,
                        "resample_params": applied_params,
                        "quality_preset": quality_preset,
                        "preserve_formants": req.preserve_formants,
                        "returned_original": True,
                        "reason": reason,
                    }
                )

            if req.preserve_formants:
                extras.append("formant=1")
            filter_str = f"rubberband={':'.join(extras)}"
            out_filename = f"resamp_{uuid.uuid4().hex[:8]}.wav"
            out_path = Path(tempfile.gettempdir()) / out_filename

            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-i", local_in,
                "-af", filter_str,
                str(out_path)
            ]

            cmd.extend(_quality_command_args(quality_preset))

            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.decode() if exc.stderr else str(exc)
                logger.error(
                    "FFmpeg resample failed for %s: %s (backend_version=%s)",
                    source_uri,
                    stderr,
                    backend_meta["backend_version"],
                )
                raise RuntimeError(f"FFmpeg resample failed: {stderr}")
            except Exception as exc:
                logger.error(
                    "Unexpected resample error: %s (backend_version=%s)",
                    exc,
                    backend_meta["backend_version"],
                )
                raise

            output_bytes = out_path.read_bytes()
            up_req = MediaUploadRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                kind="audio",
                source_uri="pending",
                tags=["generated", "resampled"]
            )
            new_asset = self.media_service.register_upload(up_req, out_filename, output_bytes)
            new_meta = {
                "backend_info": backend_meta,
                "resample_params": applied_params,
                "bpm": req.target_bpm,
                "pitch_semitones": pitch,
                "quality_preset": quality_preset,
                "preserve_formants": req.preserve_formants
            }

            new_art = self.media_service.register_artifact(
                ArtifactCreateRequest(
                    tenant_id=req.tenant_id,
                    env=req.env,
                    parent_asset_id=art.parent_asset_id,
                    kind="audio_resampled",
                    uri=new_asset.source_uri,
                    meta=new_meta
                )
            )

            return ResampleResult(
                artifact_id=new_art.id,
                uri=new_art.uri,
                duration_ms=0.0,
                meta=new_meta
            )
        finally:
            self._cleanup_temp_files()
            if 'out_path' in locals() and out_path.exists():
                try:
                    out_path.unlink()
                except Exception as exc:
                    logger.debug("Failed to remove temp resample %s: %s", out_path, exc)


# Simple factory helper to obtain a module-level resample service (used by other engines)
_resample_service_singleton: Optional[AudioResampleService] = None

def get_audio_resample_service() -> AudioResampleService:
    global _resample_service_singleton
    if _resample_service_singleton is None:
        _resample_service_singleton = AudioResampleService()
    return _resample_service_singleton
