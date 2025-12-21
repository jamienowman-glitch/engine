from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from engines.audio_shared.health import (
    build_backend_health_meta,
    check_dependencies,
    DependencyInfo,
    DependencyMissingError,
    prepare_local_asset,
)
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.media_v2.service import MediaService, get_media_service
from engines.audio_normalise.models import NormaliseRequest, NormaliseResult, FeatureTags
from engines.audio_normalise.dsp import normalize_audio, extract_features_librosa
from engines.storage.gcs_client import GcsClient

logger = logging.getLogger(__name__)
MIN_TARGET_LUFS = -30.0
MAX_TARGET_LUFS = -6.0
MIN_PEAK_CEILING = -6.0
MAX_PEAK_CEILING = -0.5


class AudioNormaliseService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self._temp_files: List[Path] = []

    def _ensure_local(self, uri: str) -> str:
        if not uri:
            raise ValueError("URI required for normalization")
        try:
            local_path, is_temp = prepare_local_asset(uri, self.gcs)
            if is_temp:
                self._temp_files.append(Path(local_path))
            return local_path
        except Exception as exc:
            logger.error("Failed to resolve asset %s: %s", uri, exc)
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
    def _validate_context(req: NormaliseRequest) -> None:
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
                "service": "audio_normalise",
                "dependency": "ffmpeg",
                "required_version": "6.0",
                "reason": reason,
                "backend_version": None,
            }
            logger.error("FFmpeg unavailable for normalise: %s", details)
            raise DependencyMissingError(details)
        return deps

    def normalise_asset(self, req: NormaliseRequest) -> NormaliseResult:
        self._validate_context(req)
        deps = self._ensure_ffmpeg()
        backend_meta = build_backend_health_meta(
            service_name="audio_normalise",
            backend_type="ffmpeg",
            primary_dependency="ffmpeg",
            dependencies=deps,
        )

        source_uri = None
        parent_id = "unknown"

        if req.artifact_id:
            art = self.media_service.get_artifact(req.artifact_id)
            if art:
                source_uri = art.uri
                parent_id = art.parent_asset_id
        elif req.asset_id:
            asset = self.media_service.get_asset(req.asset_id)
            if asset:
                source_uri = asset.source_uri
                parent_id = asset.id

        if not source_uri:
            raise ValueError("Input asset/artifact not found")

        local_in = self._ensure_local(source_uri)
        out_path = None
        norm_stats = {}
        target_lufs = max(MIN_TARGET_LUFS, min(req.target_lufs, MAX_TARGET_LUFS))
        peak_ceiling = max(MIN_PEAK_CEILING, min(req.peak_ceiling_dbfs, MAX_PEAK_CEILING))

        try:
            if not req.skip_normalization:
                out_filename = f"norm_{uuid.uuid4().hex[:8]}.{req.output_format}"
                out_path = Path(tempfile.gettempdir()) / out_filename
                try:
                    norm_stats = normalize_audio(local_in, str(out_path), target_lufs, peak_ceiling)
                except Exception as exc:
                    logger.error(
                        "Normalization failed for %s: %s (backend_version=%s)",
                        local_in,
                        exc,
                        backend_meta["backend_version"],
                    )
                    raise

            scan_path = str(out_path) if out_path and out_path.exists() else local_in
            features = extract_features_librosa(scan_path)

            final_uri = source_uri
            new_art_id = None

            if out_path and out_path.exists():
                content = out_path.read_bytes()
                up_req = MediaUploadRequest(
                    tenant_id=req.tenant_id,
                    env=req.env,
                    kind="audio",
                    source_uri="pending",
                    tags=["generated", "normalized"]
                )
                new_asset = self.media_service.register_upload(up_req, out_path.name, content)
                art = self.media_service.register_artifact(
                    ArtifactCreateRequest(
                        tenant_id=req.tenant_id,
                        env=req.env,
                        parent_asset_id=parent_id,
                        kind="audio_sample_norm",
                        uri=new_asset.source_uri,
                            meta={
                            "backend_info": backend_meta,
                            "norm_stats": norm_stats,
                            "features": features,
                            "target_lufs": target_lufs,
                            "peak_ceiling_dbfs": peak_ceiling
                        }
                    )
                )
                final_uri = art.uri
                new_art_id = art.id

            return NormaliseResult(
                artifact_id=new_art_id,
                uri=final_uri,
                lufs_measured=norm_stats.get("output_i"),
                peak_dbfs=norm_stats.get("output_tp"),
                tags=FeatureTags(**features) if features else None,
                meta={
                    "backend_info": backend_meta,
                    "norm_stats": norm_stats,
                    "features": features,
                    "target_lufs": target_lufs,
                    "peak_ceiling_dbfs": peak_ceiling,
                }
            )
        finally:
            if out_path and out_path.exists():
                try:
                    out_path.unlink()
                except Exception as exc:
                    logger.debug("Failed to cleanup normalized output %s: %s", out_path, exc)
            self._cleanup_temp_files()


# Simple factory helper to obtain a module-level normalise service (used by other engines)
_normalise_service_singleton: Optional[AudioNormaliseService] = None

def get_audio_normalise_service() -> AudioNormaliseService:
    global _normalise_service_singleton
    if _normalise_service_singleton is None:
        _normalise_service_singleton = AudioNormaliseService()
    return _normalise_service_singleton
