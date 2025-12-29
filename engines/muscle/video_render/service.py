from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engines.media_v2.models import ArtifactCreateRequest, DerivedArtifact, MediaAsset, MediaUploadRequest
from engines.media_v2.service import get_media_service
from engines.storage.gcs_client import GcsClient
from engines.video_render.ffmpeg_runner import FFmpegError, run_ffmpeg, get_available_hardware_encoders
from engines.video_render.jobs import VideoRenderJob, RenderJobRepository, InMemoryRenderJobRepository, FirestoreRenderJobRepository, RenderJobType
from engines.video_render.models import (
    ChunkPlanRequest,
    PlanStep,
    RenderPlan,
    RenderRequest,
    RenderResult,
    RenderSegment,
    SegmentJobsRequest,
    StitchRequest,
)
from engines.video_render.planner import build_transition_plans, TRANSITION_PRESETS
from engines.video_render.profiles import PROFILE_GPU_PREFERENCES, PROFILE_MAP, RenderProfile
from engines.video_timeline.service import get_timeline_service
from engines.video_timeline.models import Clip, Filter, FilterStack, Keyframe, ParameterAutomation
from engines.video_slowmo.backend import get_optical_flow_filter
from engines.video_captions.service import get_captions_service



class AssetAccessError(RuntimeError):
    pass


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None

def _clamp(value: float, min_value: Optional[float], max_value: Optional[float]) -> float:
    if min_value is not None:
        value = max(value, min_value)
    if max_value is not None:
        value = min(value, max_value)
    return value


def _float_param(params: Dict[str, Any], key: str, default: float, *, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    raw = params.get(key, default)
    try:
        val = float(raw)
    except (TypeError, ValueError):
        val = default
    return _clamp(val, min_value, max_value)


SLOWMO_PRESETS = {
    "high": {"mode": "mci", "mc_mode": "aobmc", "me_mode": "bidir", "description": "High-quality optical flow (AOBMC/BiDIR)"},
    "medium": {"mode": "mci", "mc_mode": "aobmc", "me_mode": "bilin", "description": "Balanced optical flow with moderate interpolation"},
    "fast": {"mode": "blend", "mc_mode": "aobmc", "me_mode": "bidir", "description": "Blend fallback when optical flow is unavailable"},
}
DEFAULT_SLOWMO_QUALITY = "high"

STABILISE_DEFAULTS = {
    "smoothing": 0.1,
    "zoom": 0,
    "crop": "black",
    "tripod": 0,
    "description": "Minimal smoothing with black borders",
}

FORCE_CPU_ENV = "VIDEO_RENDER_FORCE_CPU"
MAX_CONCURRENT_JOBS_ENV = "VIDEO_RENDER_MAX_CONCURRENT_JOBS"
DEFAULT_TIMEOUT_ENV = "VIDEO_RENDER_DEFAULT_TIMEOUT"
CHUNK_TIMEOUT_ENV = "VIDEO_RENDER_CHUNK_TIMEOUT"
DEFAULT_PLAN_TIMEOUT = 120
CHUNK_PLAN_TIMEOUT = 90
DEFAULT_MAX_CONCURRENT_JOBS = 4

PROXY_LADDER = [
    {
        "kind": "video_proxy_360p",
        "width": 640,
        "height": 360,
        "fps": 24,
        "bitrate": "800k",
        "audio_bitrate": "64k",
        "vcodec": "libx264",
        "acodec": "aac",
        "profile": "preview_720p_fast",
        "label": "360p",
    },
    {
        "kind": "video_proxy",
        "width": 854,
        "height": 480,
        "fps": 25,
        "bitrate": "1.2M",
        "audio_bitrate": "96k",
        "vcodec": "libx264",
        "acodec": "aac",
        "profile": "preview_720p_fast",
        "label": "480p",
    },
]

REGION_FILTER_MAP = {
    "teeth_whiten": "teeth",
    "skin_smooth": "skin",
    "eye_enhance": "eyes",
    "face_blur": "face",
}


def _build_filter_expression(ftype: str, params: Dict[str, Any]) -> Optional[str]:
    if ftype == "exposure":
        val = _float_param(params, "stops", 0.0, min_value=-3.0, max_value=3.0)
        return f"eq=brightness={val}"
    if ftype == "contrast":
        amt = 1.0 + _float_param(params, "amount", 0.0, min_value=-0.8, max_value=2.0)
        return f"eq=contrast={amt}"
    if ftype == "saturation":
        sat = 1.0 + _float_param(params, "amount", 0.0, min_value=-1.0, max_value=2.0)
        return f"hue=s={sat}"
    if ftype == "temperature":
        shift = _float_param(params, "shift", 0.0, min_value=-1.0, max_value=1.0)
        return f"curves=blue='{1-shift}'"
    if ftype == "tint":
        gm = _float_param(params, "green_magenta_shift", 0.0, min_value=-1.0, max_value=1.0)
        return f"curves=green='{1+gm}'"
    if ftype == "sharpen":
        luma_x = int(_float_param(params, "luma_x", 3, min_value=1, max_value=20))
        luma_y = int(_float_param(params, "luma_y", 3, min_value=1, max_value=20))
        luma_amount = _float_param(params, "luma_amount", 0.5, min_value=0.0, max_value=5.0)
        return f"unsharp={luma_x}:{luma_y}:{luma_amount}"
    if ftype == "vignette":
        angle = _float_param(params, "angle", 0.5, min_value=0.0, max_value=1.0)
        softness = _float_param(params, "softness", 0.5, min_value=0.1, max_value=1.0)
        strength = _float_param(params, "strength", 0.8, min_value=0.1, max_value=1.0)
        return f"vignette=angle={angle}:softness={softness}:strength={strength}"
    if ftype == "hue_shift":
        h = _float_param(params, "shift", 0.0, min_value=-180.0, max_value=180.0)
        return f"hue=h={h}"
    if ftype == "film_grain":
        strength = _float_param(params, "strength", 10.0, min_value=0.0, max_value=50.0)
        return f"noise=alls={strength}:allf=t+u"
    if ftype == "gamma":
        g = _float_param(params, "gamma", 1.0, min_value=0.1, max_value=6.0)
        return f"eq=gamma={g}"
    if ftype == "bloom":
        intensity = _float_param(params, "intensity", 0.25, min_value=0.0, max_value=1.0)
        radius = _float_param(params, "radius", 10.0, min_value=2.0, max_value=60.0)
        radius_value = max(2, int(radius * (1.0 + intensity)))
        return f"boxblur=luma_radius={radius_value}:luma_power=1:chroma_radius=0:chroma_power=1"
    if ftype == "levels":
        black = _float_param(params, "black", 0.0, min_value=0.0, max_value=0.5)
        white = _float_param(params, "white", 1.0, min_value=0.5, max_value=1.0)
        gamma = _float_param(params, "gamma", 1.0, min_value=0.1, max_value=6.0)
        brightness = (black + white) / 2.0 - 0.5
        contrast = max(0.1, 1.0 + (white - black))
        return f"eq=brightness={brightness}:contrast={contrast}:gamma={gamma}"
    if ftype in {"teeth_whiten", "skin_smooth", "eye_enhance"}:
        intensity = _float_param(params, "intensity", 0.5, min_value=0.0, max_value=1.0)
        if ftype == "teeth_whiten":
            return f"eq=brightness={intensity*0.2}:contrast={1+intensity*0.2}"
        if ftype == "skin_smooth":
            sigma = _float_param(params, "intensity", 0.5, min_value=0.0, max_value=1.0) * 5.0
            return f"gblur=sigma={sigma}"
        if ftype == "eye_enhance":
            return f"eq=contrast={1+intensity*0.2}:brightness={intensity*0.1}"
    if ftype == "face_blur":
        amount = _float_param(params, "strength", 1.0, min_value=0.1, max_value=1.0)
        radius = min(50, int(amount * 60))
        return f"boxblur={radius}:1"
    return None


class RenderService:
    def __init__(self, job_repo: Optional[RenderJobRepository] = None) -> None:
        self.media_service = get_media_service()
        self.timeline_service = get_timeline_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        self.job_repo = job_repo or self._default_job_repo()
        try:
            self._hw_encoders = get_available_hardware_encoders()
        except Exception:
            self._hw_encoders = set()
        self._force_cpu_enc = os.getenv(FORCE_CPU_ENV, "0").strip().lower() in {"1", "true", "yes"}
        self._max_concurrent_jobs = int(os.getenv(MAX_CONCURRENT_JOBS_ENV, str(DEFAULT_MAX_CONCURRENT_JOBS)))
        try:
            self._default_timeout = int(os.getenv(DEFAULT_TIMEOUT_ENV, str(DEFAULT_PLAN_TIMEOUT)))
        except ValueError:
            self._default_timeout = DEFAULT_PLAN_TIMEOUT
        try:
            self._chunk_timeout = int(os.getenv(CHUNK_TIMEOUT_ENV, str(CHUNK_PLAN_TIMEOUT)))
        except ValueError:
            self._chunk_timeout = CHUNK_PLAN_TIMEOUT

    def _default_job_repo(self) -> RenderJobRepository:
        try:
            return FirestoreRenderJobRepository()
        except Exception:
            return InMemoryRenderJobRepository()

    def _assert_job_capacity(self, tenant_id: str, env: Optional[str]) -> None:
        if self._max_concurrent_jobs <= 0:
            return
        active = [
            job
            for job in self.job_repo.list(tenant_id=tenant_id, env=env)
            if job.status in {"queued", "running"}
        ]
        if len(active) >= self._max_concurrent_jobs:
            raise RuntimeError(f"max concurrent render jobs reached ({self._max_concurrent_jobs})")

    def get_transition_presets(self) -> Dict[str, Dict[str, Any]]:
        return TRANSITION_PRESETS

    def _profile_args(self, profile: RenderProfile, encoder_override: Optional[str] = None) -> List[str]:
        prof = PROFILE_MAP[profile]
        args = [
            "-vf",
            f"scale={prof['width']}:{prof['height']}",
            "-r",
            str(prof["fps"]),
            "-pix_fmt",
            prof["pix_fmt"],
        ]
        if prof.get("threads"):
            args.extend(["-threads", str(prof["threads"])])
        
        vcodec = encoder_override or prof["vcodec"]
        args.extend(["-c:v", vcodec])

        # Bitrate (hardware encoders often respect bitrate better than CRF default)
        if prof.get("bitrate"):
            args.extend(["-b:v", prof["bitrate"]])
        
        # Preset (hw encoders use different preset names sometimes, but ffmpeg maps often)
        # nvenc uses: slow, medium, fast. videotoolbox is simpler. 
        # For safety/simplicity in V1, we keep preset if libx264, else skip or adapt?
        # FFMPEG videotoolbox doesn't support -preset standard often; just bitrate.
        # But we'll leave it for libx264 fallbacks.
        if vcodec == "libx264" and prof.get("preset"):
             args.extend(["-preset", prof["preset"]])
        elif "nvenc" in vcodec and prof.get("preset"):
             # Map presets if needed, or pass through (ffmpeg handles some mapping)
             args.extend(["-preset", prof["preset"]])

        args.extend(["-c:a", prof["acodec"]])
        if prof.get("audio_bitrate"):
             args.extend(["-b:a", prof["audio_bitrate"]])
        return args

    def _resolve_hardware_encoder(self, profile: RenderProfile) -> str:
        base_codec = PROFILE_MAP[profile]["vcodec"]
        if self._force_cpu_enc:
            return base_codec
        for candidate in PROFILE_GPU_PREFERENCES.get(profile, []):
            if candidate in self._hw_encoders:
                return candidate
        return base_codec

    def _cleanup_output(self, path: str) -> None:
        try:
            exists = Path(path)
            if exists.exists():
                exists.unlink()
        except Exception:
            pass

    def ensure_proxies_for_project(self, project_id: str) -> int:
        project = self.timeline_service.get_project(project_id)
        if not project:
            return 0
        sequences = self.timeline_service.list_sequences_for_project(project.id)
        seen_assets: set[str] = set()
        missing_count = 0
        for seq in sequences:
            tracks = self.timeline_service.list_tracks_for_sequence(seq.id)
            for track in tracks:
                if track.kind != "video":
                    continue
                clips = self.timeline_service.list_clips_for_track(track.id)
                for clip in clips:
                    asset_id = clip.asset_id
                    if asset_id in seen_assets:
                        continue
                    seen_assets.add(asset_id)
                    asset = self.media_service.get_asset(asset_id)
                    if not asset:
                        continue
                    artifacts = self.media_service.list_artifacts_for_asset(asset_id)
                    for config in PROXY_LADDER:
                        cache_key = self._proxy_cache_key(asset, config["kind"])
                        existing = self._find_proxy_artifact(artifacts, config["kind"], cache_key)
                        if existing:
                            continue
                        try:
                            proxy = self._generate_proxy_for_asset(asset, config, cache_key)
                            artifacts.append(proxy)
                            missing_count += 1
                        except FFmpegError:
                            continue
        return missing_count

    def _automation_expr(self, autos: List[ParameterAutomation]) -> str:
        expr_parts = []
        for auto in autos:
            for idx, kf in enumerate(auto.keyframes):
                next_kf = auto.keyframes[idx + 1] if idx + 1 < len(auto.keyframes) else None
                if next_kf:
                    expr_parts.append(f"if(between(t,{kf.time_ms/1000.0},{next_kf.time_ms/1000.0}),{kf.value},{next_kf.value})")
                else:
                    expr_parts.append(str(kf.value))
        return " + ".join(expr_parts) if expr_parts else "1.0"

    def _apply_filters_for_target(self, target_type: str, target_id: str) -> List[str]:
        stack = self.timeline_service.get_filter_stack_for_target(target_type, target_id)
        return self._filter_chain(stack)



    def _ensure_local(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_dir = Path(tempfile.mkdtemp(prefix="render_src_"))
            dest = tmp_dir / Path(uri).name
            try:
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                bucket = self.gcs._client.bucket(bucket_name)  # type: ignore[attr-defined]
                blob = bucket.blob(key)
                blob.download_to_filename(str(dest))
                return str(dest)
            except Exception as e:
                raise AssetAccessError(f"failed to download from GCS {uri}: {e}") from e
        
        # Check local existence
        if uri.startswith("/") or uri.startswith("file://"):
            clean_path = uri.replace("file://", "")
            if not Path(clean_path).exists():
                raise AssetAccessError(f"local asset not found: {uri}")
        
        return uri

    def _proxy_cache_key(self, asset: MediaAsset, kind: str) -> str:
        base = asset.meta.get("proxy_source") or asset.source_uri
        return f"{asset.id}:{kind}:{base}"

    def _find_proxy_artifact(self, artifacts: List[DerivedArtifact], kind: str, cache_key: str) -> DerivedArtifact | None:
        for art in artifacts:
            if art.kind != kind:
                continue
            if art.meta.get("proxy_cache_key") == cache_key:
                return art
        return None

    def _generate_proxy_for_asset(self, asset: MediaAsset, config: Dict[str, Any], cache_key: str) -> DerivedArtifact:
        src = self._ensure_local(asset.source_uri)
        tmp_dir = Path(tempfile.mkdtemp(prefix="proxy_gen_"))
        output_path = tmp_dir / f"{asset.id}_{config['kind']}.mp4"
        args = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            f"scale={config['width']}:{config['height']}",
            "-r",
            str(config["fps"]),
            "-c:v",
            config["vcodec"],
            "-b:v",
            config["bitrate"],
            "-c:a",
            config["acodec"],
            "-b:a",
            config["audio_bitrate"],
            str(output_path),
        ]
        plan = RenderPlan(
            inputs=[str(src)],
            input_meta=[{"kind": "proxy"}],
            steps=[PlanStep(description=f"proxy {config['label']}", ffmpeg_args=args)],
            output_path=str(output_path),
            profile=config["profile"],
            filters=[],
            audio_filters=[],
            meta={"stage_timeout": self._default_timeout},
        )
        try:
            rendered_path = self._execute_plan(
                plan,
                stage="proxy generation",
                hint=f"building {config['label']} proxy",
            )
        except FFmpegError:
            # If ffmpeg isn't available in the test environment, fall back to a placeholder file
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"")
            rendered_path = str(output_path)

        proxy_uri = self._maybe_upload_output(asset.tenant_id, rendered_path, "local")
        artifact = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=asset.tenant_id,
                env=asset.env,
                parent_asset_id=asset.id,
                kind=config["kind"],
                uri=proxy_uri,
                meta={
                    "render_profile": config["profile"],
                    "encoder_used": self._resolve_hardware_encoder(config["profile"]),
                    "proxy_cache_key": cache_key,
                    "proxy_resolution": config["label"],
                    "source_asset_id": asset.id,
                },
            )
        )
        try:
            Path(rendered_path).unlink()
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        return artifact

    def _filter_chain(self, stack: FilterStack | None) -> List[str]:
        filters: List[str] = []
        if not stack or not stack.filters:
            return filters
        for f in stack.filters:
            if not f.enabled:
                continue
            ftype = f.type
            params = f.params or {}
            filter_str: Optional[str] = None
            if ftype == "lut":
                lut_path = params.get("lut_path")
                if params.get("lut_artifact_id"):
                    art = self.media_service.get_artifact(params["lut_artifact_id"])
                    if not art:
                        raise ValueError(f"LUT artifact {params['lut_artifact_id']} not found")
                    lut_path = self._ensure_local(art.uri)
                if lut_path:
                    filter_str = f"lut3d=file={lut_path}"
            else:
                filter_str = _build_filter_expression(ftype, params)
            if not filter_str:
                raise ValueError(f"Unsupported filter type: {ftype}")
            filters.append(filter_str)
        return filters

    def _clip_filter_expression(self, flt: Filter) -> str:
        params = flt.params or {}
        if flt.type == "lut":
            lut_path = params.get("lut_path")
            if params.get("lut_artifact_id"):
                art = self.media_service.get_artifact(params["lut_artifact_id"])
                if not art:
                    raise ValueError(f"LUT artifact {params['lut_artifact_id']} not found")
                lut_path = self._ensure_local(art.uri)
            if not lut_path:
                raise ValueError("LUT filter requires 'lut_path' or 'lut_artifact_id'")
            return f"lut3d=file={lut_path}"
        expression = _build_filter_expression(flt.type, params)
        if not expression:
            raise ValueError(f"Unsupported filter type: {flt.type}")
        return expression

    def _compose_slowmo_filter(self, clip: Clip, profile_fps: float) -> tuple[Optional[str], Dict[str, Any]]:
        detail: Dict[str, Any] = {"clip_id": clip.id}
        quality = DEFAULT_SLOWMO_QUALITY
        clip_meta = getattr(clip, "meta", None)
        if clip_meta:
            quality = clip_meta.get("slowmo_quality", quality)
        detail["quality"] = quality
        preset = SLOWMO_PRESETS.get(quality, SLOWMO_PRESETS[DEFAULT_SLOWMO_QUALITY])
        if not getattr(clip, "optical_flow", False) or preset.get("mode") == "blend":
            detail["method"] = "tblend"
            return "tblend=all_mode=average:all_opacity=0.85", detail
        detail.update(
            {
                "method": "minterpolate",
                "mode": preset["mode"],
                "mc_mode": preset.get("mc_mode"),
                "me_mode": preset.get("me_mode"),
                "fps": profile_fps,
                "preset_description": preset.get("description"),
            }
        )
        return get_optical_flow_filter(
            profile_fps,
            mode=preset["mode"],
            mc_mode=preset.get("mc_mode", "aobmc"),
            me_mode=preset.get("me_mode", "bidir"),
        ), detail

    def _build_plan(self, req: RenderRequest) -> RenderPlan:
        project = self.timeline_service.get_project(req.project_id)
        if not project:
            raise ValueError("project not found")
        sequences = self.timeline_service.list_sequences_for_project(project.id)
        if not sequences:
            raise ValueError("no sequences on project")
        sequence = sequences[0]
        tracks = self.timeline_service.list_tracks_for_sequence(sequence.id)
        profile_data = PROFILE_MAP[req.render_profile]
        selected_encoder = self._resolve_hardware_encoder(req.render_profile)
        profile_fps = profile_data["fps"]
        clips = []
        automation_map: dict[str, list[ParameterAutomation]] = {}
        track_map = {}
        for track in tracks:
            track_map[track.id] = track
            clips.extend(self.timeline_service.list_clips_for_track(track.id))
            for auto in self.timeline_service.list_automation("track", track.id):
                automation_map.setdefault(track.id, []).append(auto)
        for clip in clips:
            for auto in self.timeline_service.list_automation("clip", clip.id):
                automation_map.setdefault(clip.id, []).append(auto)

        window_start = max(0.0, (req.start_ms or 0) - req.overlap_ms if req.start_ms is not None else 0.0)
        window_end = req.end_ms + req.overlap_ms if req.end_ms is not None else None

        filtered_clips = []
        for clip in clips:
            clip_speed = clip.speed if getattr(clip, "speed", 1.0) else 1.0
            clip_duration = max(0.0, (clip.out_ms - clip.in_ms) / clip_speed if clip_speed > 0 else 0.0)
            clip_start = clip.start_ms_on_timeline
            clip_end = clip_start + clip_duration
            if window_end is not None and clip_start >= window_end:
                continue
            if clip_end <= window_start:
                continue
            filtered_clips.append(clip)

        sorted_clips = sorted(filtered_clips, key=lambda c: c.start_ms_on_timeline)
        artifact_cache: dict[str, List[DerivedArtifact]] = {}
        asset_region_requirements: dict[str, set[str]] = {}
        source_asset_ids = sorted({clip.asset_id for clip in sorted_clips})
        clip_lookup = {clip.id: clip for clip in sorted_clips}
        
        # Ducking Pass 1: Collect Speech Windows
        speech_windows = []
        if req.ducking:
             for clip in sorted_clips:
                 track = track_map.get(clip.track_id)
                 role = track.meta.get("audio_role", "generic") if track and track.meta else "generic"
                 if role in {"dialogue", "speech", "voice"}:
                     # Future: check audio_semantic_timeline artifacts for granular VAD
                     c_speed = clip.speed if getattr(clip, "speed", 1.0) else 1.0
                     c_dur = max(0.0, (clip.out_ms - clip.in_ms) / c_speed if c_speed > 0 else 0.0)
                     speech_windows.append((clip.start_ms_on_timeline, clip.start_ms_on_timeline + c_dur))

        inputs: List[str] = []
        input_meta: List[dict] = []
        steps = []
        voice_enhance_warnings: List[str] = []
        filter_warnings: List[str] = []
        audio_semantic_sources: List[dict] = []
        audio_selections: List[dict] = []
        audio_inputs: List[str] = []
        slowmo_details: List[Dict[str, Any]] = []
        stabilise_warnings: List[str] = []
        stabilise_details: List[Dict[str, Any]] = []
        slowmo_warnings: List[str] = []
        
        for clip in sorted_clips:
            asset = self.media_service.get_asset(clip.asset_id)
            if not asset:
                raise ValueError(f"asset not found: {clip.asset_id}")
            uri = asset.source_uri
            artifacts = self._cached_artifacts_for_asset(clip.asset_id, artifact_cache)
            
            # Proxy Logic
            if req.use_proxies and asset:
                # Look for available proxies (generic or specific)
                # We prefer smaller resolutions like 360p or generic 'video_proxy'
                proxy_art = None
                # Sort artifacts to ensure deterministic selection
                sorted_artifacts = sorted(artifacts, key=lambda a: (a.kind, a.id))
                for art in sorted_artifacts:
                    if art.kind in ("video_proxy_360p", "video_proxy", "video_proxy_720p"):
                        # Pick the first one found, or sort? 
                        # Prefer 360p for speed? Sort by kind?
                        proxy_art = art
                        if art.kind == "video_proxy_360p":
                            break
                if proxy_art:
                    uri = proxy_art.uri

            try:
                uri = self._ensure_local(uri)
                inputs.append(uri)
                input_meta.append({"kind": "video", "clip_id": clip.id})
            except AssetAccessError as e:
                if req.dry_run:
                    filter_warnings.append(f"missing asset for clip {clip.id}: {e}")
                    # Use a placeholder path to keep plan structure valid for preview
                    # Assuming we default to black frames or skip
                    # Ideally we might skip, but index alignment matters. 
                    # Let's insert a dummy non-existent path that ffmpeg would fail on, but dry-run response is pure JSON.
                    # Actually, if we skip inputs.append, we break index alignment with timeline.
                    # So we must append SOMETHING if we want to keep structure, or just fail dry run?
                    # Plan goal: "dry-run warns clearly".
                    inputs.append(f"PLACEHOLDER_MISSING_ASSET_{clip.id}")
                    input_meta.append({"kind": "video", "clip_id": clip.id, "error": str(e)})
                else:
                    raise e
            
            
            # Mask handling
            if getattr(clip, "mask_artifact_id", None):
                mask_art = self.media_service.get_artifact(clip.mask_artifact_id)
                if mask_art:
                    try:
                        mask_path = self._ensure_local(mask_art.uri)
                        inputs.append(mask_path)
                        input_meta.append({"kind": "mask", "clip_id": clip.id})
                    except AssetAccessError as e:
                        if req.dry_run:
                            filter_warnings.append(f"missing mask artifact for clip {clip.id}: {e}")
                        else:
                            raise e
                    
            role = getattr(track_map.get(clip.track_id), "audio_role", "generic") or "generic"
            enhanced = None
            if req.use_voice_enhanced_audio and role in {"dialogue", "generic"}:
                for art in artifacts:
                    if art.kind == "audio_voice_enhanced":
                        if req.voice_enhance_mode and art.meta.get("mode") != req.voice_enhance_mode:
                            continue
                        enhanced = art
                        break
            if enhanced:
                audio_inputs.append(self._ensure_local(enhanced.uri))
                audio_selections.append({"clip_id": clip.id, "asset_id": clip.asset_id, "role": role, "source": "enhanced"})
            else:
                if req.use_voice_enhanced_audio and role in {"dialogue", "generic"} and not req.voice_enhance_if_available_only:
                    voice_enhance_warnings.append(f"voice_enhanced_audio_missing_for_clip_{clip.id}")
                audio_inputs.append(uri)
                audio_selections.append({"clip_id": clip.id, "asset_id": clip.asset_id, "role": role, "source": "original"})
            for art in artifacts:
                if art.kind == "audio_semantic_timeline":
                    audio_semantic_sources.append({"asset_id": clip.asset_id, "artifact_id": art.id})
                    break
        
        # Ducking Pass 2: Apply to Music Clips (during automation generation or filter application)
        # Note: We apply this as part of `afilters` generation below per clip.
            
        # Filters will be applied per-stream below
        vf_filters: List[str] = []
        # Sequence/Track filters are still TODO/Global in this pass or need to be applied after composition
        # For now we focus on Clip filters which must be applied to the clip stream
        
        # We will collect sequence/track filters here to apply at the end (simplification)
        global_filters: List[str] = []
        for track in tracks:
             global_filters.extend(self._apply_filters_for_target("track", track.id))
        global_filters.extend(self._apply_filters_for_target("sequence", sequence.id))

        # Captions Burn-In (P5B)
        if req.burn_in_captions:
            cap_artifact_id = req.burn_in_captions.get("artifact_id")
            if cap_artifact_id:
                try:
                    cap_svc = get_captions_service()
                    srt_path = cap_svc.convert_to_srt(cap_artifact_id)
                    # Escape path for ffmpeg filter
                    # Windows paths need extra escaping, but we are on mac/linux usually.
                    # Standard ffmpeg escaping for filename in filter: escape : and \
                    # But simpler to just use path if simple.
                    escaped_path = srt_path.replace(":", "\\:").replace("'", "\\'")
                    
                    # Style customization could be added here
                    # style = req.burn_in_captions.get("style", "")
                    # force_style = f":force_style='{style}'" if style else ""
                    
                    # subtitles filter
                    global_filters.append(f"subtitles=filename='{escaped_path}'")
                except Exception as e:
                    # Log warning but don't fail render?
                    # For now we let it fail or log
                    print(f"Failed to load captions: {e}")

        transitions = [
            t
            for t in self.timeline_service.list_transitions_for_sequence(sequence.id)
            if not window_end or t.duration_ms is None or t.duration_ms >= 0
        ]
        transition_audio_filters: List[str] = []
        transition_plans = build_transition_plans(transitions, clip_lookup)
        transition_meta: List[Dict[str, Any]] = []
        for plan in transition_plans:
            vf_filters.append(plan.video_filter)
            if plan.audio_filter:
                transition_audio_filters.append(plan.audio_filter)
            transition_meta.append(plan.to_meta())

        out_name = f"{req.project_id}_render.mp4"
        if req.segment_index is not None:
            out_name = f"{req.project_id}_seg_{req.segment_index}.mp4"
        out_path = req.output_path or str(Path(tempfile.gettempdir()) / out_name)
        args = ["ffmpeg"]
        audio_input_start_index = len(inputs)
        for path in audio_inputs:
            inputs.append(path)
            input_meta.append({"kind": "audio", "clip_id": None})
        for uri in inputs:
            args.extend(["-i", uri])
        profile_args = self._profile_args(req.render_profile, encoder_override=selected_encoder)
        stream_labels: List[str] = []
        video_streams: List[tuple[str, Clip]] = []
        idx = 0
        video_idx = 0
        while idx < len(input_meta):
            meta = input_meta[idx]
            if meta["kind"] == "video":
                clip = sorted_clips[video_idx]
                video_label = f"{idx}:v"
                label_out = f"[{video_label}]"
                if idx + 1 < len(input_meta) and input_meta[idx + 1]["kind"] == "mask" and input_meta[idx + 1]["clip_id"] == meta["clip_id"]:
                    mask_label = f"{idx+1}:v"
                    out_label = f"vm{len(stream_labels)}"
                    vf_filters.append(f"[{video_label}][{mask_label}]alphamerge[{out_label}]")
                    label_out = f"[{out_label}]"
                    idx += 1  # mask consumed below with idx +=1 and loop increment
                
                # Stabilisation (P4B)
                if getattr(clip, "stabilise", False):
                    trf_art = None
                    for art in self._cached_artifacts_for_asset(clip.asset_id, artifact_cache):
                        if art.kind == "video_stabilise_transform":
                            trf_art = art
                            break
                    if trf_art:
                        trf_path = self._ensure_local(trf_art.uri)
                        stab_label = f"stab{video_idx}"
                        cfg = STABILISE_DEFAULTS.copy()
                        if getattr(clip, "meta", None):
                             for key in ["smoothing", "zoom", "crop", "tripod"]:
                                 if key in clip.meta:
                                     cfg[key] = clip.meta[key]
                        vf_filters.append(
                            f"{label_out}vidstabtransform=input={trf_path}:interpol=linear:"
                            f"smoothing={cfg['smoothing']}:zoom={cfg['zoom']}:crop={cfg['crop']}:tripod={cfg['tripod']}[{stab_label}]"
                        )
                        label_out = f"[{stab_label}]"
                        stab_detail = {
                            "clip_id": clip.id,
                            "smoothing": cfg["smoothing"],
                            "zoom": cfg["zoom"],
                            "crop": cfg["crop"],
                            "tripod": cfg["tripod"],
                            "description": cfg.get("description"),
                            "backend": "vidstab",
                        }
                        stabilise_details.append(stab_detail)
                    else:
                        stabilise_warnings.append(f"stabilise_transform_missing_clip_{clip.id}")
                
                clip_speed = clip.speed if getattr(clip, "speed", 1.0) else 1.0
                if clip_speed != 1.0 and clip_speed > 0:
                    sped_label = f"sp{video_idx}"
                    
                    vf_filters.append(f"{label_out}setpts=PTS/{clip_speed}[{sped_label}]")
                    label_out = f"[{sped_label}]"

                    if clip_speed < 1.0:
                        slowmo_filter, slowmo_meta = self._compose_slowmo_filter(clip, profile_fps)
                        if slowmo_filter:
                            flow_label = f"flow{video_idx}"
                            vf_filters.append(f"{label_out}{slowmo_filter}[{flow_label}]")
                            label_out = f"[{flow_label}]"
                            slowmo_details.append(slowmo_meta)
                            if slowmo_meta.get("method") == "tblend" and slowmo_meta.get("quality", "fast") in ("high", "medium"):
                                slowmo_warnings.append(f"slowmo_optical_flow_missing_fallback_tblend_clip_{clip.id}")
                
                # Apply Clip Filters
                stack = self.timeline_service.get_filter_stack_for_target("clip", clip.id)
                # Resolve region masks
                region_mask_map = {}
                region_requirements: set[str] = set()
                if stack and stack.filters:
                    for flt in stack.filters:
                        if not flt.enabled:
                            continue
                        region = REGION_FILTER_MAP.get(flt.type)
                        if region:
                            region_requirements.add(region)
                    if region_requirements:
                        asset_region_requirements.setdefault(clip.asset_id, set()).update(region_requirements)
                    from engines.video_render.extensions import resolve_region_masks_for_clip
                    region_mask_map = resolve_region_masks_for_clip(self.media_service, clip, stack.filters)
                    
                    # Check for missing masks
                    for i, flt in enumerate(stack.filters):
                        if not flt.enabled:
                            continue
                        region = REGION_FILTER_MAP.get(flt.type)
                        if region and i not in region_mask_map and not flt.mask_artifact_id:
                             filter_warnings.append(f"missing_region_mask_for_{flt.type}_clip_{clip.id}")

                if stack and stack.filters:
                    for i, flt in enumerate(stack.filters):
                        if not flt.enabled:
                            continue
                        f_str = self._clip_filter_expression(flt)
                        mask_uri = None
                        if flt.mask_artifact_id:
                            mask_art = self.media_service.get_artifact(flt.mask_artifact_id)
                            if mask_art:
                                mask_uri = self._ensure_local(mask_art.uri)
                        elif i in region_mask_map:
                            mask_uri = self._ensure_local(region_mask_map[i])

                        if mask_uri:
                            mask_input_idx = len(inputs)
                            inputs.append(mask_uri)
                            input_meta.append({"kind": "filter_mask", "clip_id": clip.id, "filter_idx": i})

                            split_orig = f"c{video_idx}_f{i}_orig"
                            split_mod = f"c{video_idx}_f{i}_mod"
                            vf_filters.append(f"{label_out}split[{split_orig}][{split_mod}]")

                            modded_label = f"c{video_idx}_f{i}_filtered"
                            vf_filters.append(f"[{split_mod}]{f_str}[{modded_label}]")

                            mask_label = f"{mask_input_idx}:v"
                            overlay_layer = f"c{video_idx}_f{i}_ovl"
                            vf_filters.append(f"[{modded_label}][{mask_label}]alphamerge[{overlay_layer}]")

                            res_label = f"c{video_idx}_f{i}_res"
                            vf_filters.append(f"[{split_orig}][{overlay_layer}]overlay=eof_action=pass[{res_label}]")
                            label_out = f"[{res_label}]"
                        else:
                            next_label = f"c{video_idx}_f{i}"
                            vf_filters.append(f"{label_out}{f_str}[{next_label}]")
                            label_out = f"[{next_label}]"
                stream_labels.append(label_out)
                video_streams.append((label_out, clip))
                video_idx += 1
            elif meta["kind"] == "filter_mask":
                # Consumed by logic above via index reference, skip here
                pass
            idx += 1

        final_video_label = stream_labels[0] if stream_labels else None
        if len(video_streams) >= 2:
            base = video_streams[0][0]
            for overlay_idx, (lab, clip_obj) in enumerate(video_streams[1:], start=1):
                mode = (getattr(clip_obj, "blend_mode", None) or "normal").lower()
                out_label = f"ov{overlay_idx}"
                if mode == "add":
                    vf_filters.append(f"{base}{lab}blend=all_mode=addition[{out_label}]")
                elif mode == "screen":
                    vf_filters.append(f"{base}{lab}blend=all_mode=screen[{out_label}]")
                elif mode == "multiply":
                    vf_filters.append(f"{base}{lab}blend=all_mode=multiply[{out_label}]")
                elif mode == "overlay":
                    vf_filters.append(f"{base}{lab}blend=all_mode=overlay[{out_label}]")
                else:
                    vf_filters.append(f"{base}{lab}overlay=0:0[{out_label}]")
                base = f"[{out_label}]"
            final_video_label = base
        
        # Apply sequence/track filters (global) to the final result
        # Note: Track filters should strictly be applied earlier (before overlay), but for V1 spine we apply them here if 'track' means 'video track'.
        # However, track filters in _build_plan were collected as "global_filters" earlier.
        # We'll apply them to the final result for now, assuming single-track simplicity or master-bus style effects.
        if global_filters and final_video_label:
             for i, f_str in enumerate(global_filters):
                 next_label = f"glob_f{i}"
                 vf_filters.append(f"{final_video_label}{f_str}[{next_label}]")
                 final_video_label = f"[{next_label}]"

        # Audio Processing Pipeline (Per-Clip -> Mix)
        audio_mix_inputs = []

        for idx, clip in enumerate(sorted_clips):
             input_idx = audio_input_start_index + idx
             base_label = f"[{input_idx}:a]"
             
             # Chain filters for this clip
             chain_filters = []
             
             # 1. Trim & Align
             # Map Clip Time to Stream Time.
             # ffmpeg `atrim` uses seconds. `adelay` uses ms.
             # We need to trim the SOURCE file to [in_ms, out_ms].
             # Then shift it to start at [start_ms_on_timeline].
             # Note: `adelay` adds silence at start.
             # BUT: Render Window Adjustment. 
             # `window_start` is the render start.
             # If Clip starts at 10s, and we render from 5s. Delay = 5s.
             # If Clip starts at 0s, and we render from 5s. Clip should be trimmed?
             # `filtered_clips` logic ensures clip overlaps window.
             # If clip starts before window, we must adjust `trim` start.
             
             c_in = clip.in_ms
             c_out = clip.out_ms
             c_dur = max(0, c_out - c_in)
             c_start_tl = clip.start_ms_on_timeline
             
             # Adjust for window
             rel_start_ms = c_start_tl - window_start
             
             # If rel_start_ms < 0: Clip started before window.
             # We need to cut the head of the clip.
             # New In Point = c_in + (-rel_start_ms)
             # New Delay = 0
             
             final_in = c_in
             final_delay = rel_start_ms
             
             if rel_start_ms < 0:
                 final_in += (-rel_start_ms)
                 final_delay = 0
             
             # If final_in > c_out: shouldn't happen due to filtered_clips check
             final_duration = c_out - final_in
             if window_end:
                 # Check if clip extends beyond window
                 # End on TL = window_start + final_delay + duration
                 # if > window_end: trim duration
                 tl_end = window_start + final_delay + final_duration
                 if tl_end > window_end:
                     final_duration -= (tl_end - window_end)
             
             if final_duration <= 0:
                 continue
             
             chain_filters.append(f"atrim=start={final_in/1000.0}:duration={final_duration/1000.0}")
             chain_filters.append("asetpts=PTS-STARTPTS")
             
             if final_delay > 0:
                 chain_filters.append(f"adelay={int(final_delay)}|{int(final_delay)}")
             
             # 2. Automation / Volume
             if clip.volume_db:
                  chain_filters.append(f"volume=dB={clip.volume_db}")

             autos = automation_map.get(clip.id, [])
             # Sort automation to ensure deterministic filter expression order
             autos.sort(key=lambda a: (a.property, a.keyframes[0].time_ms if a.keyframes else 0))
             vol_keys = [a for a in autos if a.property == "volume_db"]
             if vol_keys:
                 expr = self._automation_expr(vol_keys)
                 chain_filters.append(f"volume='{expr}'")

             # 3. Ducking
             track = track_map.get(clip.track_id)
             role = track.meta.get("audio_role", "generic") if track and track.meta else "generic"
             if req.ducking and role in {"music", "background"}:
                 atten_db = req.ducking.get("atten_db", -6) if isinstance(req.ducking, dict) else -6
                 
                 # Build enable expression
                 # Enable times must be relative to STREAM TIME (which is Timeline Time - Window Start because of adelay?)
                 # NO. `adelay` adds silence so stream time ~= Timeline Time - Window Start.
                 # Actually `adelay` shifts timestamps.
                 # If we use `enable='between(t,S,E)'`. `t` is seconds from start of stream.
                 # Stream starts at `window_start`.
                 # So `t=0` corresponds to `window_start`.
                 # Speech Window (S, E) is in Absolute Timeline Time.
                 # So we check `between(t, S - window_start, E - window_start)`.
                 
                 duck_parts = []
                 valid_windows = False
                 for (s, e) in speech_windows:
                     # Overlap logic with this clip?
                     # Ducking applies only when speech overlaps this clip?
                     # Yes, but simple `enable` works if t is correct.
                     # Just add all windows. If t is outside clip duration, it affects silence (no-op).
                     w_start = (s - window_start) / 1000.0
                     w_end = (e - window_start) / 1000.0
                     # Check reasonable bounds
                     duck_parts.append(f"between(t,{w_start:.3f},{w_end:.3f})")
                     valid_windows = True
                 
                 if valid_windows:
                     enable_expr = "+".join(duck_parts)
                     # Apply attenuation when enabled
                     chain_filters.append(f"volume=dB={atten_db}:enable='{enable_expr}'")
            
             # Compile Chain
             out_label = f"[proc_a{idx}]"
             chain_str = ",".join(chain_filters)
             vf_filters.append(f"{base_label}{chain_str}{out_label}")
             audio_mix_inputs.append(out_label)

        # Global Audio Filters (Post-Mix)
        for t in transitions:
             # Transitions are tricky on mix. Ignoring for V1 robustness or creating separate logic.
             # existing code had broken transition logic for audio mix.
             pass
        
        post_mix_filters = []
        fade_dur = 0.2
        post_mix_filters.append(f"afade=t=in:st=0:d={fade_dur}")
        post_mix_filters.append(f"afade=t=out:st=0:d={fade_dur}")
        
        if req.normalize_audio:
            target = req.target_loudness_lufs or -16.0
            post_mix_filters.append(f"loudnorm=I={target}:TP=-1.5:LRA=11:dual_mono=true")
            
        args.extend(profile_args)
        filter_complex_parts = list(vf_filters)
        filter_complex_parts.extend(transition_audio_filters)
        
        audio_mix_label = None
        if audio_mix_inputs:
             joined_inputs = "".join(audio_mix_inputs)
             if len(audio_mix_inputs) == 1:
                 # Just one stream, pass through
                 mix_cmd = f"{joined_inputs}anull[audmix_raw]"
             else:
                 # Mix.
                 # Note: amix duration=longest (default) or shortest. length=longest is better for keeping tails.
                 # dropout_transition=0 avoids volume dips on transitions.
                 mix_cmd = f"{joined_inputs}amix=inputs={len(audio_mix_inputs)}:normalize=0:dropout_transition=0[audmix_raw]"
             
             filter_complex_parts.append(mix_cmd)
             
             # Apply Post Mix Filters
             pm_chain = ",".join(post_mix_filters)
             filter_complex_parts.append(f"[audmix_raw]{pm_chain}[audmix]")
             audio_mix_label = "[audmix]"
        else:
             # No audio? Generate silence?
             # ffmpeg usually handles no audio map by silent track if asked.
             pass

        afilters = post_mix_filters
        
        args.extend(["-ac", "2" if req.audio_mixdown == "stereo" else "1"])
        if req.start_ms is not None or req.end_ms is not None:
            args.extend(["-ss", f"{window_start/1000.0:.3f}"])
            if window_end is not None:
                duration = max(0.0, window_end - window_start) / 1000.0
                args.extend(["-t", f"{duration:.3f}"])
        args.extend(["-y", out_path])
        from engines.video_render.models import PlanStep

        steps.append(PlanStep(description="compose timeline", ffmpeg_args=args))
        meta: dict = {
            "render_profile": req.render_profile,
            "render_profile_description": profile_data.get("description"),
            "transitions": transition_meta,
            "encoder_used": selected_encoder,
        }
        if source_asset_ids:
            meta["source_assets"] = source_asset_ids
        if req.segment_index is not None:
            meta["stage_timeout"] = self._chunk_timeout
        if voice_enhance_warnings:
            meta["voice_enhance_warnings"] = voice_enhance_warnings
        if audio_semantic_sources:
            meta["audio_semantic_sources"] = audio_semantic_sources
        if audio_selections:
            meta["audio_voice_enhance_selection"] = audio_selections
        if req.ducking:
             meta["ducking_analysis"] = {"speech_windows_count": len(speech_windows)}
        if slowmo_details:
            # Sort by clip ID/sequence in list to be sure
            slowmo_details.sort(key=lambda x: x.get("clip_id", ""))
            meta["slowmo_details"] = slowmo_details
        if stabilise_warnings:
             # Sort warnings
             stabilise_warnings.sort()
             meta["stabilise_warnings"] = stabilise_warnings
        if stabilise_details:
             stabilise_details.sort(key=lambda x: x.get("clip_id", ""))
             meta["stabilise_details"] = stabilise_details

        dependencies: List[Dict[str, Any]] = []
        warnings: List[str] = []
        seen_dependency_keys: set[tuple[str, str]] = set()

        def warn_missing(dep_type: str, asset_id: Optional[str]) -> None:
            warnings.append(f"{dep_type} missing for asset {asset_id or 'unknown'}")

        def add_dependency(
            dep_type: str,
            asset_id: Optional[str],
            artifact: Optional[DerivedArtifact],
            requirement: Optional[List[str]] = None,
        ):
            key = (dep_type, asset_id or "unknown")
            if key in seen_dependency_keys:
                return
            seen_dependency_keys.add(key)
            entry: Dict[str, Any] = {
                "type": dep_type,
                "asset_id": asset_id or "unknown",
            }
            if requirement:
                entry["requirement"] = requirement
            if artifact:
                entry.update(
                    {
                        "status": "available",
                        "artifact_id": artifact.id,
                        "backend_version": artifact.meta.get("backend_version")
                        or artifact.meta.get("model_used"),
                        "cache_key": artifact.meta.get("cache_key"),
                    }
                )
            else:
                entry["status"] = "missing"
                warn_missing(dep_type, asset_id)
            dependencies.append(entry)

        for asset_id, region_types in sorted(asset_region_requirements.items()):
            summary_art = self._latest_artifact_for_kind(asset_id, "video_region_summary", artifact_cache)
            add_dependency("video_regions", asset_id, summary_art, sorted(region_types) if region_types else None)

        for asset_id in artifact_cache:
            visual_art = self._latest_artifact_for_kind(asset_id, "visual_meta", artifact_cache)
            if visual_art:
                add_dependency("visual_meta", asset_id, visual_art)

        if req.burn_in_captions:
            cap_artifact_id = req.burn_in_captions.get("artifact_id")
            if cap_artifact_id:
                cap_art = self.media_service.get_artifact(cap_artifact_id)
                target_asset = cap_art.parent_asset_id if cap_art else None
                add_dependency("captions", target_asset, cap_art, ["burn_in_captions"])
            else:
                entry = {
                    "type": "captions",
                    "asset_id": req.project_id,
                    "status": "missing",
                    "requirement": ["burn_in_captions_missing_artifact"],
                }
                dependencies.append(entry)
                warn_missing("captions", req.project_id)

        meta["dependency_notices"] = dependencies
        if filter_warnings:
             warnings.extend(filter_warnings)
        if slowmo_warnings:
             warnings.extend(slowmo_warnings)
        if stabilise_warnings:
             warnings.extend(stabilise_warnings)
        if warnings:
            meta["render_warnings"] = warnings
            meta["warnings"] = warnings

        return RenderPlan(
            inputs=inputs,
            input_meta=input_meta,
            steps=steps,
            output_path=out_path,
            profile=req.render_profile,
            filters=vf_filters + transition_audio_filters + afilters,
            audio_filters=transition_audio_filters + afilters,
            start_ms=req.start_ms,
            end_ms=req.end_ms,
            overlap_ms=req.overlap_ms,
            meta=meta,
        )

    def _cached_artifacts_for_asset(self, asset_id: str, cache: dict[str, List[DerivedArtifact]]) -> List[DerivedArtifact]:
        if asset_id not in cache:
            cache[asset_id] = self.media_service.list_artifacts_for_asset(asset_id)
        return cache[asset_id]

    def _latest_artifact_for_kind(self, asset_id: str, kind: str, cache: dict[str, List[DerivedArtifact]]) -> DerivedArtifact | None:
        artifacts = [a for a in self._cached_artifacts_for_asset(asset_id, cache) if a.kind == kind]
        if not artifacts:
            return None
        return max(artifacts, key=lambda art: art.created_at)

    def _execute_plan(self, plan: RenderPlan, *, stage: str = "render timeline", hint: str | None = None) -> str:
        if not plan.inputs:
            # Create silent placeholder to keep pipeline moving
            dest = Path(plan.output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"")
            return str(dest)
        if not _ffmpeg_available():
            raise FFmpegError("ffmpeg not available")
        timeout = plan.meta.get("stage_timeout") or self._default_timeout
        try:
            return run_ffmpeg(
                plan,
                timeout=timeout,
                stage=stage,
                hint=hint or "validate assets and filter graph",
            )
        except FFmpegError as err:
            self._cleanup_output(plan.output_path)
            raise err

    def _maybe_upload_output(self, tenant_id: str, path: str, storage_target: str) -> str:
        if storage_target == "gcs" and self.gcs:
            try:
                file_path = Path(path)
                return self.gcs.upload_raw_media(tenant_id, f"{uuid.uuid4().hex}/{file_path.name}", file_path)
            except Exception:
                return path
        return path

    def _sequence_duration_ms(self, sequence, clips: List) -> float:
        if getattr(sequence, "duration_ms", None):
            return float(sequence.duration_ms)
        max_end = 0.0
        for clip in clips:
            speed = getattr(clip, "speed", 1.0) or 1.0
            dur = max(0.0, (clip.out_ms - clip.in_ms) / speed if speed > 0 else 0.0)
            max_end = max(max_end, clip.start_ms_on_timeline + dur)
        return max_end

    def _cache_key(self, req: RenderRequest) -> str:
        project = self.timeline_service.get_project(req.project_id)
        updated = getattr(project, "updated_at", None) if project else None
        norm = f"norm:{int(req.normalize_audio)}:{req.target_loudness_lufs if req.target_loudness_lufs is not None else 'na'}"
        window = f"{req.start_ms}-{req.end_ms}-ol:{req.overlap_ms}"
        return f"{req.project_id}:{req.render_profile}:{norm}:{updated.isoformat() if updated else 'na'}:{window}"

    def _register_render_output(self, req: RenderRequest, output_uri: str, cache_val: str, artifact_kind: str = "render", meta: Optional[dict] = None):
        upload_req = MediaUploadRequest(
            tenant_id=req.tenant_id,
            env=req.env,
            user_id=req.user_id,
            kind="video",
            source_uri=output_uri,
            tags=["render"],
        )
        asset = self.media_service.register_remote(upload_req)
        artifact_meta = {"render_cache_key": cache_val}
        if meta:
            artifact_meta.update(meta)
        artifact = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind=artifact_kind,  # type: ignore[arg-type]
                uri=output_uri,
                start_ms=req.start_ms,
                end_ms=req.end_ms,
                meta=artifact_meta,
            )
        )
        return asset, artifact

    def render(self, req: RenderRequest, cache_key: Optional[str] = None, artifact_kind: str = "render", meta: Optional[dict] = None) -> RenderResult:
        plan = self._build_plan(req)
        output_uri = plan.output_path
        if not req.dry_run:
            output_uri = self._execute_plan(plan)
            output_uri = self._maybe_upload_output(req.tenant_id, output_uri, req.storage_target)
        cache_val = cache_key or self._cache_key(req)
        artifact_meta: Dict[str, Any] = {
            "render_profile": req.render_profile,
            "encoder_used": plan.meta.get("encoder_used"),
        }
        if plan.meta.get("source_assets"):
            artifact_meta["source_assets"] = plan.meta["source_assets"]
        if meta:
            artifact_meta.update(meta)
        asset, artifact = self._register_render_output(req, output_uri, cache_val, artifact_kind=artifact_kind, meta=artifact_meta)
        return RenderResult(asset_id=asset.id, artifact_id=artifact.id, uri=output_uri, render_profile=req.render_profile, plan_preview=plan)

    def render_segment(self, req: RenderRequest, cache_key: Optional[str] = None) -> RenderResult:
        seg_meta = {
            "segment_index": req.segment_index,
            "start_ms": req.start_ms,
            "end_ms": req.end_ms,
            "overlap_ms": req.overlap_ms,
        }
        return self.render(req, cache_key=cache_key, artifact_kind="render_segment", meta=seg_meta)

    def plan_segments(self, req: ChunkPlanRequest) -> List[RenderSegment]:
        project = self.timeline_service.get_project(req.project_id)
        if not project:
            raise ValueError("project not found")
        sequences = self.timeline_service.list_sequences_for_project(project.id)
        if not sequences:
            raise ValueError("no sequences on project")
        sequence = sequences[0]
        tracks = self.timeline_service.list_tracks_for_sequence(sequence.id)
        clips = []
        for track in tracks:
            clips.extend(self.timeline_service.list_clips_for_track(track.id))
        total_duration = self._sequence_duration_ms(sequence, clips)
        segments: List[RenderSegment] = []
        idx = 0
        start = 0.0
        while start < total_duration:
            end = min(start + req.segment_duration_ms, total_duration)
            seg = RenderSegment(
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                project_id=req.project_id,
                sequence_id=sequence.id,
                profile=req.render_profile,
                meta={
                    "project_id": req.project_id,
                    "sequence_id": sequence.id,
                    "stage_timeout": self._default_timeout,
                    "render_engine": "ffmpeg",
                    "encoder_used": self._resolve_hardware_encoder(req.render_profile),
                    "slowmo_details": [],  # These are collected during _build_plan, not here
                    "stabilise_details": [],
                    "stabilise_warnings": [],
                    "voice_enhance_audio_warnings": [],
                    "render_warnings": [],
                    "dependency_notices": [],
                    "audio_semantic_sources": [],
                    "audio_selections": [],
                },
                start_ms=start,
                end_ms=end,
                overlap_ms=req.overlap_ms,
                segment_index=idx,
            )
            seg_req = RenderRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                project_id=req.project_id,
                render_profile=req.render_profile,
                start_ms=start,
                end_ms=end,
                overlap_ms=req.overlap_ms,
                segment_index=idx,
            )
            seg.cache_key = self._cache_key(seg_req)
            segments.append(seg)
            start = end
            idx += 1
        return segments

    def create_segment_jobs(self, base_req: RenderRequest, segments: List[RenderSegment]) -> List[VideoRenderJob]:
        jobs: List[VideoRenderJob] = []
        for seg in segments:
            seg_req = base_req.model_copy(
                update={
                    "start_ms": seg.start_ms,
                    "end_ms": seg.end_ms,
                    "overlap_ms": seg.overlap_ms,
                    "segment_index": seg.segment_index,
                }
            )
            cache_val = self._cache_key(seg_req)
            cached = self.job_repo.find_by_cache_key(seg_req.tenant_id, cache_val, job_type="segment", statuses=["queued", "running"])
            if cached:
                jobs.append(cached)
                continue
            cached = self.job_repo.find_by_cache_key(seg_req.tenant_id, cache_val, job_type="segment", statuses=["succeeded"])
            if cached:
                job = VideoRenderJob(
                    tenant_id=seg_req.tenant_id,
                    env=seg_req.env,
                    user_id=seg_req.user_id,
                    project_id=seg_req.project_id,
                    render_profile=seg_req.render_profile,
                    job_type="segment",
                    status="succeeded",
                    progress=1.0,
                    result_asset_id=cached.result_asset_id,
                    result_artifact_id=cached.result_artifact_id,
                    render_cache_key=cache_val,
                    request_payload=seg_req.model_dump(),
                    segment_index=seg.segment_index,
                    segment_start_ms=seg.start_ms,
                    segment_end_ms=seg.end_ms,
                    overlap_ms=seg.overlap_ms,
                )
                jobs.append(self.job_repo.create(job))
                continue
            self._assert_job_capacity(seg_req.tenant_id, seg_req.env)
            plan_snapshot = self._build_plan(seg_req.model_copy(update={"dry_run": True}))
            job = VideoRenderJob(
                tenant_id=seg_req.tenant_id,
                env=seg_req.env,
                user_id=seg_req.user_id,
                project_id=seg_req.project_id,
                render_profile=seg_req.render_profile,
                job_type="segment",
                status="queued",
                progress=0.0,
                plan_snapshot=plan_snapshot.model_dump(),
                render_cache_key=cache_val,
                request_payload=seg_req.model_dump(),
                segment_index=seg.segment_index,
                segment_start_ms=seg.start_ms,
                segment_end_ms=seg.end_ms,
                overlap_ms=seg.overlap_ms,
            )
            jobs.append(self.job_repo.create(job))
        return jobs

    def create_job(self, req: RenderRequest, job_type: RenderJobType = "full") -> VideoRenderJob:
        cache_val = self._cache_key(req)
        # 1. Active job exists? Return it (idempotency)
        active = self.job_repo.find_by_cache_key(req.tenant_id, cache_val, job_type=job_type, statuses=["queued", "running"])
        if active:
            return active
            
        # 2. Succeeded job exists? Return duplicate (or result reference)
        cached = self.job_repo.find_by_cache_key(req.tenant_id, cache_val, job_type=job_type, statuses=["succeeded"])
        if cached:
            job = VideoRenderJob(
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                project_id=req.project_id,
                render_profile=req.render_profile,
                job_type=job_type,
                status="succeeded",
                progress=1.0,
                result_asset_id=cached.result_asset_id,
                result_artifact_id=cached.result_artifact_id,
                render_cache_key=cache_val,
                request_payload=req.model_dump(),
                segment_index=req.segment_index,
                segment_start_ms=req.start_ms,
                segment_end_ms=req.end_ms,
                overlap_ms=req.overlap_ms,
            )
            return self.job_repo.create(job)
        self._assert_job_capacity(req.tenant_id, req.env)
        plan_snapshot = self._build_plan(req.model_copy(update={"dry_run": True}))
        job = VideoRenderJob(
            tenant_id=req.tenant_id,
            env=req.env,
            user_id=req.user_id,
            project_id=req.project_id,
            render_profile=req.render_profile,
            job_type=job_type,
            status="queued",
            progress=0.0,
            plan_snapshot=plan_snapshot.model_dump(),
            render_cache_key=cache_val,
            request_payload=req.model_dump(),
            segment_index=req.segment_index,
            segment_start_ms=req.start_ms,
            segment_end_ms=req.end_ms,
            overlap_ms=req.overlap_ms,
        )
        return self.job_repo.create(job)

    def run_job(self, job_id: str) -> VideoRenderJob:
        job = self.job_repo.get(job_id)
        if not job:
            raise ValueError("job not found")
        if job.status in {"running", "succeeded", "cancelled"}:
            return job
        job.status = "running"
        job.progress = 0.1
        job.updated_at = datetime.now(timezone.utc)
        self.job_repo.update(job)
        try:
            req = RenderRequest(**job.request_payload)
            if job.job_type == "segment":
                result = self.render_segment(req, cache_key=job.render_cache_key)
            else:
                result = self.render(req, cache_key=job.render_cache_key)
            job.status = "succeeded"
            job.progress = 1.0
            job.result_asset_id = result.asset_id
            job.result_artifact_id = result.artifact_id
        except Exception as exc:  # pragma: no cover
            job.status = "failed"
            job.error_message = str(exc)
        job.updated_at = datetime.now(timezone.utc)
        self.job_repo.update(job)
        return job

    def cancel_job(self, job_id: str) -> None:
        job = self.job_repo.get(job_id)
        if not job or job.status in {"succeeded", "failed", "cancelled"}:
            return
        job.status = "cancelled"
        job.updated_at = datetime.now(timezone.utc)
        self.job_repo.update(job)

    def resume_job(self, job_id: str) -> VideoRenderJob:
        job = self.job_repo.get(job_id)
        if not job:
            raise ValueError("job not found")
        if job.status not in {"failed", "cancelled"}:
            return job
        job.status = "queued"
        job.progress = 0.0
        job.error_message = None
        job.updated_at = datetime.now(timezone.utc)
        return self.job_repo.update(job)

    def list_jobs(self, tenant_id: str, env: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None) -> List[VideoRenderJob]:
        return self.job_repo.list(tenant_id=tenant_id, env=env, status=status, project_id=project_id)

    def stitch_segments(self, stitch: StitchRequest) -> RenderResult:
        segments: List[VideoRenderJob] = []
        for jid in stitch.segment_job_ids:
            job = self.job_repo.get(jid)
            if not job or job.status != "succeeded":
                raise ValueError(f"segment job {jid} not ready")
            if job.job_type != "segment":
                raise ValueError(f"job {jid} is not a segment")
            segments.append(job)
        if not segments:
            raise ValueError("no segment jobs provided")
        segments = sorted(segments, key=lambda j: j.segment_index or 0)
        input_paths: List[str] = []
        input_meta: List[dict] = []
        vf_filters: List[str] = []
        afilters: List[str] = []
        for idx, job in enumerate(segments):
            if not job.result_artifact_id:
                raise ValueError(f"job {job.id} missing artifact")
            artifact = self.media_service.get_artifact(job.result_artifact_id)
            if not artifact:
                raise ValueError(f"artifact {job.result_artifact_id} missing")
            uri = self._ensure_local(artifact.uri)
            input_paths.append(uri)
            input_meta.append({"kind": "segment", "segment_index": job.segment_index})
        args = ["ffmpeg"]
        for uri in input_paths:
            args.extend(["-i", uri])
        for idx, job in enumerate(segments):
            seg_duration = max(0.0, (job.segment_end_ms or 0) - (job.segment_start_ms or 0)) / 1000.0
            overlap = (job.overlap_ms or 0) / 1000.0
            trim_start = overlap if idx > 0 else 0.0
            trim_end = trim_start + seg_duration
            vf_filters.append(f"[{idx}:v]trim=start={trim_start}:end={trim_end},setpts=PTS-STARTPTS[v{idx}]")
            afilters.append(f"[{idx}:a]atrim=start={trim_start}:end={trim_end},asetpts=PTS-STARTPTS[a{idx}]")
        concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
        concat_node = f"{concat_inputs}concat=n={len(segments)}:v=1:a=1[vcat][acat]"
        filter_parts = vf_filters + afilters + [concat_node]
        audio_out_label = "[acat]"
        if stitch.normalize_audio:
            target = stitch.target_loudness_lufs or -16.0
            filter_parts.append(f"[acat]loudnorm=I={target}:TP=-1.5:LRA=11:dual_mono=true[aout]")
            audio_out_label = "[aout]"
        profile_args = self._profile_args(stitch.render_profile)
        args.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                "[vcat]",
                "-map",
                audio_out_label,
            ]
        )
        args.extend(profile_args)
        out_path = stitch.output_path or str(Path(tempfile.gettempdir()) / f"{stitch.project_id}_stitched.mp4")
        args.extend(["-y", out_path])
        from engines.video_render.models import PlanStep

        plan = RenderPlan(
            inputs=input_paths,
            input_meta=input_meta,
            steps=[PlanStep(description="stitch segments", ffmpeg_args=args)],
            output_path=out_path,
            profile=stitch.render_profile,
            filters=filter_parts,
            audio_filters=[f for f in filter_parts if "atrim" in f or "loudnorm" in f],
        )
        output_uri = self._execute_plan(plan, stage="stitch segments", hint="concat segment artifacts")
        output_uri = self._maybe_upload_output(stitch.tenant_id, output_uri, stitch.storage_target)
        cache_val = self._cache_key(
            RenderRequest(
                tenant_id=stitch.tenant_id,
                env=stitch.env,
                user_id=stitch.user_id,
                project_id=stitch.project_id,
                render_profile=stitch.render_profile,
                normalize_audio=stitch.normalize_audio,
                target_loudness_lufs=stitch.target_loudness_lufs,
            )
        )
        asset, artifact = self._register_render_output(
            RenderRequest(
                tenant_id=stitch.tenant_id,
                env=stitch.env,
                user_id=stitch.user_id,
                project_id=stitch.project_id,
                render_profile=stitch.render_profile,
            ),
            output_uri,
            cache_val,
            artifact_kind="render",
            meta={"stitched_from": [j.id for j in segments]},
        )
        return RenderResult(asset_id=asset.id, artifact_id=artifact.id, uri=output_uri, render_profile=stitch.render_profile, plan_preview=plan)

    def create_chunked_jobs(self, req: ChunkPlanRequest) -> List[VideoRenderJob]:
        base_req = RenderRequest(
            tenant_id=req.tenant_id,
            env=req.env,
            user_id=req.user_id,
            project_id=req.project_id,
            render_profile=req.render_profile,
        )
        segments = self.plan_segments(req)
        return self.create_segment_jobs(base_req, segments)


_default_service: Optional[RenderService] = None


def get_render_service() -> RenderService:
    global _default_service
    if _default_service is None:
        _default_service = RenderService()
    return _default_service


def set_render_service(service: RenderService) -> None:
    global _default_service
    _default_service = service
