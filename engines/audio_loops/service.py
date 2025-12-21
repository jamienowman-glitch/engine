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
from engines.audio_loops.models import LoopDetectRequest, LoopDetectResult, LoopEvent
from engines.audio_loops.backend import AudioLoopsBackend, LibrosaLoopsBackend, StubLoopsBackend, HAS_LIBROSA
from engines.storage.gcs_client import GcsClient

logger = logging.getLogger(__name__)
LOOP_MIN_DURATION_MS = 500
LOOP_MAX_DURATION_MS = 30_000


class AudioLoopsService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self._real_backend: Optional[AudioLoopsBackend] = LibrosaLoopsBackend() if HAS_LIBROSA else None
        self._stub_backend: AudioLoopsBackend = StubLoopsBackend()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self._temp_files: List[Path] = []

    @staticmethod
    def _validate_context(req: LoopDetectRequest) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("Invalid tenant_id")
        if not req.env:
            raise ValueError("Invalid env")

    def _select_backend(self) -> Tuple[AudioLoopsBackend, Dict[str, Any]]:
        # Fast-path: if a real backend is present and the module-level flag indicates librosa available,
        # short-circuit to avoid expensive dependency probes in tests. Otherwise, probe runtime deps.
        if self._real_backend and HAS_LIBROSA:
            deps = {"librosa": DependencyInfo(True, None, None)}
            backend = self._real_backend
            backend_type = "librosa"
            primary_dependency = "librosa"
        elif self._real_backend:
            # Some backends (like DefaultPhrasesBackend in the phrases service) can work without librosa.
            deps = check_dependencies()
            backend = self._real_backend
            backend_type = "librosa" if (deps.get("librosa") and deps["librosa"].available) else "default"
            primary_dependency = "librosa" if backend_type == "librosa" else "transcript"
        else:
            deps = check_dependencies()
            backend = self._stub_backend
            backend_type = "stub"
            primary_dependency = "stub"
        meta = build_backend_health_meta(
            service_name="audio_loops",
            backend_type=backend_type,
            primary_dependency=primary_dependency,
            dependencies=deps,
        )
        return backend, meta

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
                logger.warning("Loop slice timeout (%s s) for %s: %s", SLICE_TIMEOUT_SECONDS, source_path, exc)
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.decode() if exc.stderr else str(exc)
                logger.error("FFmpeg loop slice failed (%s): %s", source_path, stderr)
            except Exception as exc:
                logger.error("Unexpected error slicing loop %s: %s", source_path, exc)
            finally:
                if out_path.exists():
                    out_path.unlink()
        return None

    def detect_loops(self, req: LoopDetectRequest) -> LoopDetectResult:
        self._validate_context(req)
        backend, backend_meta = self._select_backend()
        req_params = req.model_dump(exclude={"meta"})
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

        local_path = self._ensure_local(target_uri)
        try:
            if backend_meta["backend_type"] == "librosa" and not os.path.exists(local_path):
                raise ValueError(f"Local audio file not found: {local_path}")

            candidates = backend.detect(local_path, req)
            loops: List[LoopEvent] = []
            artifact_ids = []

            for cand in candidates:
                if cand.confidence < req.min_confidence:
                    continue

                start_ms, end_ms = clamp_segment_window(
                    cand.start_ms,
                    cand.end_ms,
                    LOOP_MIN_DURATION_MS,
                    LOOP_MAX_DURATION_MS,
                )
                loop_event = LoopEvent(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    source_start_ms=start_ms,
                    source_end_ms=end_ms,
                    loop_bars=cand.loop_bars,
                    bpm=cand.bpm,
                    confidence=cand.confidence
                )
                loops.append(loop_event)

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
                            tags=["generated", "loop_slice"]
                        )
                        slice_asset = self.media_service.register_upload(
                            up_req,
                            f"loop_{uuid.uuid4().hex[:8]}.wav",
                            slice_bytes
                        )
                        new_uri = slice_asset.source_uri
                        slice_asset_id = slice_asset.id

                art = self.media_service.register_artifact(
                    ArtifactCreateRequest(
                        tenant_id=req.tenant_id,
                        env=req.env,
                        parent_asset_id=target_id,
                        kind="audio_loop",
                        uri=new_uri,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        meta={
                            "backend_version": backend_meta["backend_version"],
                            "backend_type": backend_meta["backend_type"],
                            "backend_health": backend_meta["dependencies"],
                            "op_type": "audio_loops.detect_v1",
                            "loop": {
                                "bpm": cand.bpm,
                                "loop_bars": cand.loop_bars,
                                "confidence": cand.confidence,
                                "start_ms": start_ms,
                                "end_ms": end_ms,
                            },
                            "params": req_params,
                            "slice_asset_id": slice_asset_id,
                        }
                    )
                )
                artifact_ids.append(art.id)

            return LoopDetectResult(
                loops=loops,
                artifact_ids=artifact_ids,
                meta={"engine": "audio_loops_v2", "backend_info": backend_meta}
            )
        finally:
            self._cleanup_temp_files()


_default_service: Optional[AudioLoopsService] = None


def get_audio_loops_service() -> AudioLoopsService:
    global _default_service
    if _default_service is None:
        _default_service = AudioLoopsService()
    return _default_service
