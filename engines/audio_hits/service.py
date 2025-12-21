from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engines.audio_shared.health import (
    DependencyInfo,
    clamp_segment_window,
    check_dependencies,
    build_backend_health_meta,
    prepare_local_asset,
    SLICE_TIMEOUT_SECONDS,
)
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.media_v2.service import MediaService, get_media_service
from engines.audio_hits.models import HitDetectRequest, HitDetectResult, HitEvent
from engines.audio_hits.backend import (
    AudioHitsBackend,
    LibrosaHitsBackend,
    StubHitsBackend,
    HAS_LIBROSA,
    OnsetResult,
)
from engines.storage.gcs_client import GcsClient

logger = logging.getLogger(__name__)
HIT_MIN_DURATION_MS = 500
HIT_MAX_DURATION_MS = 30_000

class AudioHitsService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self._real_backend: Optional[AudioHitsBackend] = LibrosaHitsBackend() if HAS_LIBROSA else None
        self._stub_backend: AudioHitsBackend = StubHitsBackend()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self._temp_files: List[Path] = []

    @staticmethod
    def _validate_context(req: HitDetectRequest) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("Invalid tenant_id")
        if not req.env:
            raise ValueError("Invalid env")

    def _select_backend(self) -> Tuple[AudioHitsBackend, Dict[str, Any]]:
        # Fast-path: if a real backend exists and the module-level flag indicates librosa is available,
        # avoid running the full dependency probe (which calls out to subprocess). This keeps tests
        # deterministic when they patch HAS_LIBROSA.
        if self._real_backend and HAS_LIBROSA:
            deps = {"librosa": DependencyInfo(True, None, None)}
            backend = self._real_backend
            primary_dependency = "librosa"
            backend_type = "librosa"
        else:
            deps = check_dependencies()
            # Prefer real backend only if runtime health reports librosa available
            use_real = bool(self._real_backend and deps.get("librosa") and deps["librosa"].available)
            if use_real:
                backend = self._real_backend
                primary_dependency = "librosa"
                backend_type = "librosa"
            else:
                backend = self._stub_backend
                primary_dependency = "stub"
                backend_type = "stub"

        health_meta = build_backend_health_meta(
            service_name="audio_hits",
            backend_type=backend_type,
            primary_dependency=primary_dependency,
            dependencies=deps,
        )
        return backend, health_meta

    def _ensure_local(self, uri: str) -> str:
        try:
            local_path, is_temp = prepare_local_asset(uri, self.gcs)
            if is_temp:
                self._temp_files.append(Path(local_path))
            return local_path
        except Exception as exc:
            logger.error("Failed to fetch %s locally: %s", uri, exc)
            raise

    def _cleanup_temp_files(self) -> None:
        while self._temp_files:
            path = self._temp_files.pop()
            try:
                if path.exists():
                    path.unlink()
            except Exception as exc:
                logger.debug("Failed to cleanup temp file %s: %s", path, exc)

    def _slice_audio(self, source_path: str, start_ms: float, end_ms: float) -> Optional[bytes]:
        # Try to slice using ffmpeg for robustness (avoids loading whole file into RAM if soundfile not present)
        # Or soundfile if available?
        # FFMPEG is universally available in this env per constraints?
        # Let's use ffmpeg subprocess.
        if shutil.which("ffmpeg"):
            out_path = Path(tempfile.gettempdir()) / f"slice_{uuid.uuid4().hex}.wav"
            duration = (end_ms - start_ms) / 1000.0
            start_sec = start_ms / 1000.0
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-ss", f"{start_sec:.3f}",
                "-t", f"{duration:.3f}",
                "-i", source_path,
                "-f", "wav",
                str(out_path)
            ]
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=SLICE_TIMEOUT_SECONDS
                )
                return out_path.read_bytes()
            except subprocess.TimeoutExpired as exc:
                logger.warning("Hit slice timed out (%s s) for %s: %s", SLICE_TIMEOUT_SECONDS, source_path, exc)
            except subprocess.CalledProcessError as exc:
                logger.error("FFmpeg slicing failed (%s): %s", source_path, exc.stderr.decode() if exc.stderr else exc)
            except Exception as exc:
                logger.error("Unexpected error while slicing %s: %s", source_path, exc)
            finally:
                if out_path.exists():
                    out_path.unlink()
        
        # Fallback to python read if available?
        # For V1 "Real Muscles", ffmpeg is preferred for slicing files.
        return None

    def detect_hits(self, req: HitDetectRequest) -> HitDetectResult:
        self._validate_context(req)
        backend, backend_meta = self._select_backend()
        req_params = req.model_dump(exclude={"meta"})
        # 1. Resolve Asset
        target_uri = None
        target_id = None
        if req.asset_id:
            asset = self.media_service.get_asset(req.asset_id)
            target_id = req.asset_id
            target_uri = asset.source_uri if asset else None
        elif req.artifact_id:
            artifact = self.media_service.get_artifact(req.artifact_id)
            target_id = artifact.parent_asset_id if artifact else "unknown"
            target_uri = artifact.uri if artifact else None
        
        if not target_uri:
            raise ValueError("Source URI not found")

        # 2. Ensure Local
        local_path = self._ensure_local(target_uri)
        try:
            if backend_meta["backend_type"] == "librosa" and not os.path.exists(local_path):
                raise ValueError(f"Local audio file not found: {local_path}")

            # 3. Backend Detect
            onsets = backend.detect(local_path, req)

            # 4. Processing & Registration
            events = []
            artifact_ids = []

            for onset in onsets:
                start_ms, end_ms = clamp_segment_window(
                    onset.start_ms,
                    onset.end_ms,
                    HIT_MIN_DURATION_MS,
                    HIT_MAX_DURATION_MS,
                )
                requested_max = max(req.max_duration_ms, HIT_MIN_DURATION_MS)
                duration_limit = min(requested_max, HIT_MAX_DURATION_MS)
                duration_ms = min(end_ms - start_ms, duration_limit)
                end_ms = start_ms + duration_ms

                ev = HitEvent(
                    time_ms=start_ms,
                    peak_db=onset.peak_db,
                    source_start_ms=start_ms,
                    source_end_ms=end_ms,
                    duration_ms=duration_ms
                )
                events.append(ev)

                new_uri = target_uri
                slice_asset_id = None

                if os.path.exists(local_path):
                    slice_bytes = self._slice_audio(local_path, start_ms, end_ms)
                    if slice_bytes:
                        up_req = MediaUploadRequest(
                            tenant_id=req.tenant_id,
                            env=req.env,
                            kind="audio",
                            source_uri="pending",
                            tags=["generated", "hit_slice"]
                        )
                        slice_asset = self.media_service.register_upload(
                            up_req, 
                            f"hit_{uuid.uuid4().hex[:8]}.wav", 
                            slice_bytes
                        )
                        new_uri = slice_asset.source_uri
                        slice_asset_id = slice_asset.id

                art = self.media_service.register_artifact(
                    ArtifactCreateRequest(
                        tenant_id=req.tenant_id,
                        env=req.env,
                        parent_asset_id=target_id,
                        kind="audio_hit",
                        uri=new_uri,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        meta={
                            "backend_version": backend_meta["backend_version"],
                            "backend_type": backend_meta["backend_type"],
                            "backend_health": backend_meta["dependencies"],
                            "op_type": "audio_hits.detect_v1",
                            "detection": {
                                "peak_db": onset.peak_db,
                                "duration_ms": duration_ms,
                                "start_ms": start_ms,
                                "end_ms": end_ms,
                            },
                            "params": req_params,
                            "slice_asset_id": slice_asset_id,
                        },
                    )
                )
                artifact_ids.append(art.id)

            return HitDetectResult(
                events=events,
                artifact_ids=artifact_ids,
                meta={
                    "engine": "audio_hits_v2",
                    "backend_info": backend_meta,
                },
            )
        finally:
            self._cleanup_temp_files()

    def _analyze_signal(self, uri: str, req: HitDetectRequest) -> List[HitEvent]:
        # Deprecated internal method, kept for compatibility if needed, 
        # but detect_hits logic replaced it.
        return []


_default_service: Optional[AudioHitsService] = None

def get_audio_hits_service() -> AudioHitsService:
    global _default_service
    if _default_service is None:
        _default_service = AudioHitsService()
    return _default_service
