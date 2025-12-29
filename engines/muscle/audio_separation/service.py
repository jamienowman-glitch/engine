from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from engines.audio_shared.health import (
    build_backend_health_meta,
    check_dependencies,
    DependencyInfo,
    prepare_local_asset,
)
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import MediaService, get_media_service
from engines.audio_separation.models import SeparationRequest, SeparationResult
from engines.audio_separation.backend import run_demucs_separation
from engines.storage.gcs_client import GcsClient

logger = logging.getLogger(__name__)


class AudioSeparationService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self._temp_files: List[Path] = []

    def _prepare_source(self, uri: str) -> str:
        local_path, is_temp = prepare_local_asset(uri, self.gcs)
        if is_temp:
            self._temp_files.append(Path(local_path))
        return local_path

    def _cleanup_temp_files(self) -> None:
        while self._temp_files:
            path = self._temp_files.pop()
            try:
                if path.exists():
                    path.unlink()
            except Exception as exc:
                logger.debug("Failed to cleanup separation temp file %s: %s", path, exc)

    @staticmethod
    def _run_stub_separation(local_source: str) -> Dict[str, str]:
        # Deterministic stub returns the same source for each stem
        return {
            "drums": local_source,
            "bass": local_source,
            "vocals": local_source,
            "other": local_source,
        }

    def separate_audio(self, req: SeparationRequest) -> SeparationResult:
        art = self.media_service.get_artifact(req.artifact_id)
        if not art:
            raise ValueError("Artifact not found")

        local_source = self._prepare_source(art.uri)
        deps = check_dependencies()
        demucs_info = deps.get("demucs")
        runtime_seconds = 0.0
        result_artifacts: Dict[str, str] = {}
        backend_meta: Dict[str, Any]
        dep_info: Optional[DependencyInfo] = None

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                if demucs_info and demucs_info.available:
                    backend_meta = build_backend_health_meta(
                        service_name="audio_separation",
                        backend_type="demucs",
                        primary_dependency="demucs",
                        dependencies=deps,
                    )
                    dep_info = demucs_info
                    start_ts = time.time()
                    try:
                        stems_map = run_demucs_separation(local_source, tmp_dir, req.model_name)
                    except RuntimeError as exc:
                        logger.error(
                            "Demucs separation error for %s: %s (backend_version=%s)",
                            req.artifact_id,
                            exc,
                            backend_meta["backend_version"],
                        )
                        raise
                    runtime_seconds = time.time() - start_ts
                else:
                    stub_info = DependencyInfo(True, "stub", "fallback demucs missing")
                    deps_stub = {**deps, "stub_backend": stub_info}
                    backend_meta = build_backend_health_meta(
                        service_name="audio_separation",
                        backend_type="stub",
                        primary_dependency="stub_backend",
                        dependencies=deps_stub,
                    )
                    dep_info = stub_info
                    logger.warning(
                        "Demucs missing for %s, using stub separation (backend_version=%s)",
                        req.artifact_id,
                        backend_meta["backend_version"],
                    )
                    stems_map = self._run_stub_separation(local_source)

                model_meta = {
                    "model_name": req.model_name,
                    "demucs_version": dep_info.version if dep_info else "unknown",
                    "runtime_seconds": runtime_seconds,
                    "backend_type": backend_meta["backend_type"],
                    "backend_version": backend_meta["backend_version"],
                }

                for role, path_str in stems_map.items():
                    p = Path(path_str)
                    content = p.read_bytes()
                    kind = f"audio_stem_{role}"
                    if role == "drums":
                        kind = "audio_stem_drum"
                    elif role == "vocals":
                        kind = "audio_stem_vocal"

                    up_req = MediaUploadRequest(
                        tenant_id=req.tenant_id, env=req.env, kind="audio",
                        source_uri="pending", tags=["generated", "stem", role]
                    )
                    new_asset = self.media_service.register_upload(up_req, p.name, content)

                    meta = {
                        "source_artifact": req.artifact_id,
                        "role": role,
                        "model": req.model_name,
                        "backend_info": backend_meta,
                        **model_meta
                    }

                    new_art = self.media_service.register_artifact(
                        ArtifactCreateRequest(
                            tenant_id=req.tenant_id, env=req.env,
                            parent_asset_id=new_asset.id,
                            kind=kind,
                            uri=new_asset.source_uri,
                            meta=meta
                        )
                    )
                    result_artifacts[role] = new_art.id

        finally:
            self._cleanup_temp_files()

        return SeparationResult(
            source_artifact_id=req.artifact_id,
            stems=result_artifacts,
            meta={
                "model": req.model_name,
                "demucs_version": model_meta["demucs_version"],
                "backend_info": backend_meta,
                "runtime_seconds": model_meta["runtime_seconds"],
            }
        )


_default_service: Optional[AudioSeparationService] = None


def get_audio_separation_service() -> AudioSeparationService:
    global _default_service
    if _default_service is None:
        _default_service = AudioSeparationService()
    return _default_service
