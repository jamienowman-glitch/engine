from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import subprocess

from engines.audio_shared.health import (
    build_backend_health_meta,
    check_dependencies,
    DependencyInfo,
    DependencyMissingError,
    prepare_local_asset,
)
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import MediaService, get_media_service
from engines.audio_macro_engine.models import MacroRequest, MacroResult
from engines.audio_macro_engine.presets import MACRO_DEFINITIONS
from engines.audio_macro_engine.compiler import compile_macro_to_ffmpeg
from engines.storage.gcs_client import GcsClient

MACRO_KNOB_RANGE = (0.0, 100.0)

logger = logging.getLogger(__name__)


def _collect_allowed_macro_knobs(macro) -> set[str]:
    allowed = set()
    for idx, node in enumerate(macro.nodes):
        for key in node.params.keys():
            allowed.add(key)
            allowed.add(f"{idx}.{key}")
    return allowed


def _sanitize_macro_overrides(overrides: dict, allowed_keys: set[str]) -> dict:
    if not overrides:
        return {}
    sanitized = {}
    low, high = MACRO_KNOB_RANGE
    for key, value in overrides.items():
        if key not in allowed_keys:
            logger.warning("Ignoring unsupported macro knob override %s", key)
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            logger.warning("Non-numeric knob override %s=%s", key, value)
            continue
        sanitized[key] = max(low, min(high, numeric))
    return sanitized


class AudioMacroEngineService:
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
            logger.error("Failed to download %s: %s", uri, exc)
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
    def _validate_context(req: MacroRequest) -> None:
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
                "service": "audio_macro_engine",
                "dependency": "ffmpeg",
                "required_version": "6.0",
                "reason": reason,
                "backend_version": None,
            }
            logger.error("FFmpeg unavailable for macro_engine: %s", details)
            raise DependencyMissingError(details)
        return deps

    def execute_macro(self, req: MacroRequest) -> MacroResult:
        self._validate_context(req)
        deps = self._ensure_ffmpeg()
        backend_meta = build_backend_health_meta(
            service_name="audio_macro_engine",
            backend_type="ffmpeg",
            primary_dependency="ffmpeg",
            dependencies=deps,
        )

        art = self.media_service.get_artifact(req.artifact_id)
        if not art:
            raise ValueError(f"Artifact not found: {req.artifact_id}")
        if req.macro_id not in MACRO_DEFINITIONS:
            raise ValueError(f"Unknown macro: {req.macro_id}")

        macro = MACRO_DEFINITIONS[req.macro_id]
        allowed_knobs = _collect_allowed_macro_knobs(macro)
        sanitized_overrides = _sanitize_macro_overrides(req.knob_overrides, allowed_knobs)
        logger.info("Executing macro %s overrides=%s", req.macro_id, sanitized_overrides)
        filter_str, out_label = compile_macro_to_ffmpeg(macro, sanitized_overrides)
        local_uri = self._ensure_local(art.uri)

        out_filename = f"macro_{req.macro_id}_{uuid.uuid4().hex[:8]}.{req.output_format}"
        out_path = Path(tempfile.gettempdir()) / out_filename

        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", local_uri,
            "-filter_complex", filter_str,
            "-map", out_label,
            str(out_path)
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode() if exc.stderr else str(exc)
            logger.error(
                "Macro FFmpeg failed for %s: %s (backend_version=%s)",
                req.macro_id,
                stderr,
                backend_meta["backend_version"],
            )
            raise RuntimeError(f"FFmpeg macro failed: {stderr}")
        except Exception as exc:
            logger.error(
                "Unexpected macro failure %s: %s (backend_version=%s)",
                req.macro_id,
                exc,
                backend_meta["backend_version"],
            )
            raise

        try:
            content = out_path.read_bytes()
            up_req = MediaUploadRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                kind="audio",
                source_uri="pending",
                tags=["generated", "macro", req.macro_id]
            )
            new_asset = self.media_service.register_upload(up_req, out_filename, content)
            meta = {
                "backend_info": backend_meta,
                "macro_id": req.macro_id,
                "source_artifact": req.artifact_id,
                "macro_definition_meta": macro.meta,
                "knob_overrides": sanitized_overrides,
            }
            new_art = self.media_service.register_artifact(
                ArtifactCreateRequest(
                    tenant_id=req.tenant_id,
                    env=req.env,
                    parent_asset_id=new_asset.id,
                    kind="audio_macro",
                    uri=new_asset.source_uri,
                    meta=meta
                )
            )
        finally:
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception as exc:
                    logger.debug("Failed to cleanup macro output %s: %s", out_path, exc)
        self._cleanup_temp_files()

        return MacroResult(
            artifact_id=new_art.id,
            uri=new_art.uri,
            duration_ms=0.0,
            meta={
                **new_art.meta,
                "backend_info": backend_meta,
                "macro_id": req.macro_id,
                "source_artifact": req.artifact_id,
            }
        )


_default_service: Optional[AudioMacroEngineService] = None


def get_audio_macro_engine_service() -> AudioMacroEngineService:
    global _default_service
    if _default_service is None:
        _default_service = AudioMacroEngineService()
    return _default_service
