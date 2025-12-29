from __future__ import annotations

import logging
import uuid
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engines.audio_shared.health import (
    build_backend_health_meta,
    check_dependencies,
    DependencyInfo,
    DependencyMissingError,
    prepare_local_asset,
)
from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.audio_fx_chain.models import FxChainRequest, FxChainResult
from engines.audio_fx_chain.presets import FX_PRESETS, FX_PRESET_METADATA
from engines.audio_fx_chain.dsp import build_ffmpeg_filter_string
from engines.storage.gcs_client import GcsClient

SAT_TYPES = {"soft", "hard", "cubic"}
HPF_RANGE = (20.0, 4000.0)
LPF_RANGE = (1000.0, 22000.0)
EQ_FREQ_RANGE = (20.0, 20000.0)
EQ_GAIN_RANGE = (-24.0, 24.0)
EQ_Q_RANGE = (0.3, 5.0)
COMP_THRESH_RANGE = (-60.0, 5.0)
COMP_RATIO_RANGE = (1.0, 20.0)
COMP_ATTACK_RANGE = (0.1, 200.0)
COMP_RELEASE_RANGE = (10.0, 1000.0)
COMP_MAKEUP_RANGE = (-6.0, 12.0)
SAT_DRIVE_RANGE = (0.0, 1.0)
REVERB_DECAY_RANGE = (0.5, 6.0)
REVERB_MIX_RANGE = (0.0, 1.0)
LIMITER_THRESH_RANGE = (-20.0, 0.0)


def _clamp_value(value: float, value_range: tuple[float, float]) -> float:
    low, high = value_range
    return max(low, min(high, value))


def _sanitize_eq(eq_bands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized = []
    for band in eq_bands:
        band_copy = band.copy()
        if "f" in band_copy:
            band_copy["f"] = _clamp_value(float(band_copy["f"]), EQ_FREQ_RANGE)
        if "g" in band_copy:
            band_copy["g"] = _clamp_value(float(band_copy["g"]), EQ_GAIN_RANGE)
        if "q" in band_copy:
            band_copy["q"] = _clamp_value(float(band_copy["q"]), EQ_Q_RANGE)
        band_copy["type"] = band_copy.get("type", "bell")
        sanitized.append(band_copy)
    return sanitized


def _sanitize_comp(comp: Dict[str, Any]) -> Dict[str, Any]:
    comp_copy = comp.copy()
    if "thresh" in comp_copy:
        comp_copy["thresh"] = _clamp_value(float(comp_copy["thresh"]), COMP_THRESH_RANGE)
    if "ratio" in comp_copy:
        comp_copy["ratio"] = _clamp_value(float(comp_copy["ratio"]), COMP_RATIO_RANGE)
    if "attack" in comp_copy:
        comp_copy["attack"] = _clamp_value(float(comp_copy["attack"]), COMP_ATTACK_RANGE)
    if "release" in comp_copy:
        comp_copy["release"] = _clamp_value(float(comp_copy["release"]), COMP_RELEASE_RANGE)
    if "makeup" in comp_copy:
        comp_copy["makeup"] = _clamp_value(float(comp_copy["makeup"]), COMP_MAKEUP_RANGE)
    return comp_copy


def _sanitize_sat(sat: Dict[str, Any]) -> Dict[str, Any]:
    sat_copy = sat.copy()
    if "drive" in sat_copy:
        sat_copy["drive"] = _clamp_value(float(sat_copy["drive"]), SAT_DRIVE_RANGE)
    sat_type = sat_copy.get("type", "soft")
    sat_copy["type"] = sat_type if sat_type in SAT_TYPES else "soft"
    return sat_copy


def _sanitize_reverb(reverb: Dict[str, Any]) -> Dict[str, Any]:
    rev_copy = reverb.copy()
    if "decay" in rev_copy:
        rev_copy["decay"] = _clamp_value(float(rev_copy["decay"]), REVERB_DECAY_RANGE)
    if "mix" in rev_copy:
        rev_copy["mix"] = _clamp_value(float(rev_copy["mix"]), REVERB_MIX_RANGE)
    return rev_copy


def _sanitize_limiter(limiter: Dict[str, Any]) -> Dict[str, Any]:
    lim_copy = limiter.copy()
    if "thresh" in lim_copy:
        lim_copy["thresh"] = _clamp_value(float(lim_copy["thresh"]), LIMITER_THRESH_RANGE)
    return lim_copy


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in params.items():
        if key == "eq" and isinstance(value, list):
            sanitized[key] = _sanitize_eq(value)
        elif key == "comp" and isinstance(value, dict):
            sanitized[key] = _sanitize_comp(value)
        elif key == "sat" and isinstance(value, dict):
            sanitized[key] = _sanitize_sat(value)
        elif key == "reverb" and isinstance(value, dict):
            sanitized[key] = _sanitize_reverb(value)
        elif key == "limiter" and isinstance(value, dict):
            sanitized[key] = _sanitize_limiter(value)
        elif key == "hpf_hz" and value is not None:
            sanitized[key] = _clamp_value(float(value), HPF_RANGE)
        elif key == "lpf_hz" and value is not None:
            sanitized[key] = _clamp_value(float(value), LPF_RANGE)
        else:
            sanitized[key] = value
    return sanitized


def _merge_overrides(base: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not overrides:
        return deepcopy(base)
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


logger = logging.getLogger(__name__)
DRY_WET_MIN = 0.0
DRY_WET_MAX = 1.0

class AudioFxChainService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self._temp_files: List[Path] = []

    @staticmethod
    def _validate_context(req: FxChainRequest) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("Invalid tenant_id")
        if not req.env:
            raise ValueError("Invalid env")

    def _resolve_source(self, req: FxChainRequest) -> Tuple[str, str]:
        source_uri = None
        parent_id = "unknown"

        if req.artifact_id:
            art = self.media_service.get_artifact(req.artifact_id)
            if art:
                source_uri = art.uri
                parent_id = art.parent_asset_id or art.id
        if source_uri:
            return source_uri, parent_id

        if req.asset_id:
            asset = self.media_service.get_asset(req.asset_id)
            if asset:
                return asset.source_uri, asset.id

        raise ValueError("Input asset/artifact not found")

    @staticmethod
    def _clamp_dry_wet(value: float) -> float:
        return max(DRY_WET_MIN, min(DRY_WET_MAX, value))

    def _ensure_ffmpeg(self) -> Dict[str, DependencyInfo]:
        deps = check_dependencies()
        ffmpeg_info = deps.get("ffmpeg")
        if not ffmpeg_info or not ffmpeg_info.available:
            reason = ffmpeg_info.error if ffmpeg_info else "ffmpeg missing"
            details = {
                "code": "missing_dependency",
                "service": "audio_fx_chain",
                "dependency": "ffmpeg",
                "required_version": "6.0",
                "reason": reason,
                "backend_version": None,
            }
            logger.error("FFmpeg unavailable for fx_chain: %s", details)
            raise DependencyMissingError(details)
        return deps

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

    def apply_fx(self, req: FxChainRequest) -> FxChainResult:
        self._validate_context(req)
        deps = self._ensure_ffmpeg()
        backend_meta = build_backend_health_meta(
            service_name="audio_fx_chain",
            backend_type="ffmpeg",
            primary_dependency="ffmpeg",
            dependencies=deps,
        )

        source_uri, parent_id = self._resolve_source(req)
        local_in = self._ensure_local(source_uri)
        if req.preset_id not in FX_PRESETS:
            raise ValueError(f"Unknown preset: {req.preset_id}")

        merged_params = _merge_overrides(FX_PRESETS[req.preset_id], req.params_override)
        sanitized_params = _sanitize_params(merged_params)
        dry_wet = self._clamp_dry_wet(req.dry_wet)
        if dry_wet != req.dry_wet:
            logger.debug("Dry/wet clamped from %s to %s", req.dry_wet, dry_wet)
        if req.params_override:
            logger.debug("Applying overrides on %s: %s", req.preset_id, req.params_override)
        filter_str = build_ffmpeg_filter_string(sanitized_params, dry_wet)
        if not filter_str:
            raise ValueError(f"Preset {req.preset_id} produced no filter chain")

        out_filename = f"fx_{req.preset_id}_{uuid.uuid4().hex[:8]}.{req.output_format}"
        out_path = Path(tempfile.gettempdir()) / out_filename
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", local_in,
            "-af", filter_str,
            str(out_path)
        ]

        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            output_bytes = out_path.read_bytes()
            up_req = MediaUploadRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                kind="audio",
                source_uri="pending",
                tags=["generated", "fx_chain", req.preset_id]
            )
            new_asset = self.media_service.register_upload(up_req, out_filename, output_bytes)
            meta = {
                "backend_info": backend_meta,
                "fx_preset_id": req.preset_id,
                "preset_metadata": FX_PRESET_METADATA.get(req.preset_id, {}),
                "params_applied": sanitized_params,
                "dry_wet": dry_wet,
                "knob_overrides": req.params_override or {},
            }

            art = self.media_service.register_artifact(
                ArtifactCreateRequest(
                    tenant_id=req.tenant_id,
                    env=req.env,
                    parent_asset_id=parent_id,
                    kind="audio_sample_fx",
                    uri=new_asset.source_uri,
                    meta=meta
                )
            )
            return FxChainResult(
                artifact_id=art.id,
                uri=art.uri,
                preset_id=req.preset_id,
                params_applied=sanitized_params,
                meta={
                    **art.meta,
                    "backend_info": backend_meta,
                    "preset_id": req.preset_id,
                    "dry_wet": dry_wet,
                },
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode() if exc.stderr else str(exc)
            logger.error(
                "FFmpeg FX chain failed (%s): %s (backend_version=%s)",
                req.preset_id,
                stderr,
                backend_meta["backend_version"],
            )
            raise RuntimeError(f"FFmpeg failed: {stderr}")
        except Exception as exc:
            logger.error(
                "Unexpected FFmpeg error (%s): %s (backend_version=%s)",
                req.preset_id,
                exc,
                backend_meta["backend_version"],
            )
            raise
        finally:
            self._cleanup_temp_files()
            if "out_path" in locals() and out_path.exists():
                try:
                    out_path.unlink()
                except Exception as exc:
                    logger.debug("Failed to cleanup fx output %s: %s", out_path, exc)

_default_service: Optional[AudioFxChainService] = None

def get_audio_fx_chain_service() -> AudioFxChainService:
    global _default_service
    if _default_service is None:
        _default_service = AudioFxChainService()
    return _default_service
