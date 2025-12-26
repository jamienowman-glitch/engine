from __future__ import annotations

from typing import Dict, List, Optional, Any

from engines.config import runtime_config
from engines.video_presets.models import FilterPreset, MotionPreset
from engines.video_timeline.models import Keyframe, ParameterAutomation, Filter
import uuid
from pydantic import BaseModel, Field

class VideoTemplate(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tenant_id: str
    env: str
    name: str
    description: Optional[str] = None
    render_profile: str
    filter_preset_id: Optional[str] = None
    motion_preset_id: Optional[str] = None
    # Potentially other layout info, but strictly speaking "Social Templates" usually bundle look + motion + format
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None


class PresetRepository:
    def create_filter(self, preset: FilterPreset) -> FilterPreset:
        raise NotImplementedError

    def list_filters(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[FilterPreset]:
        raise NotImplementedError

    def get_filter(self, preset_id: str) -> Optional[FilterPreset]:
        raise NotImplementedError

    def delete_filter(self, preset_id: str) -> None:
        raise NotImplementedError

    def create_motion(self, preset: MotionPreset) -> MotionPreset:
        raise NotImplementedError

    def list_motion(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[MotionPreset]:
        raise NotImplementedError

    def get_motion(self, preset_id: str) -> Optional[MotionPreset]:
        raise NotImplementedError

    def delete_motion(self, preset_id: str) -> None:
        raise NotImplementedError

    def create_template(self, template: VideoTemplate) -> VideoTemplate:
        raise NotImplementedError

    def list_templates(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[VideoTemplate]:
        raise NotImplementedError

    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        raise NotImplementedError

    def delete_template(self, template_id: str) -> None:
        raise NotImplementedError


class InMemoryPresetRepository(PresetRepository):
    def __init__(self) -> None:
        self.filter_presets: Dict[str, FilterPreset] = {}
        self.motion_presets: Dict[str, MotionPreset] = {}
        self.templates: Dict[str, VideoTemplate] = {}

    def create_filter(self, preset: FilterPreset) -> FilterPreset:
        self.filter_presets[preset.id] = preset
        return preset

    def list_filters(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[FilterPreset]:
        results = [p for p in self.filter_presets.values() if p.tenant_id == tenant_id]
        if env:
            results = [p for p in results if p.env == env]
        if tag:
            results = [p for p in results if tag in (p.tags or [])]
        return results

    def get_filter(self, preset_id: str) -> Optional[FilterPreset]:
        return self.filter_presets.get(preset_id)

    def delete_filter(self, preset_id: str) -> None:
        self.filter_presets.pop(preset_id, None)

    def create_motion(self, preset: MotionPreset) -> MotionPreset:
        self.motion_presets[preset.id] = preset
        return preset

    def list_motion(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[MotionPreset]:
        results = [p for p in self.motion_presets.values() if p.tenant_id == tenant_id]
        if env:
            results = [p for p in results if p.env == env]
        if tag:
            results = [p for p in results if tag in (p.tags or [])]
        return results

    def get_motion(self, preset_id: str) -> Optional[MotionPreset]:
        return self.motion_presets.get(preset_id)

    def delete_motion(self, preset_id: str) -> None:
        self.motion_presets.pop(preset_id, None)

    def create_template(self, template: VideoTemplate) -> VideoTemplate:
        self.templates[template.id] = template
        return template

    def list_templates(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[VideoTemplate]:
        results = [t for t in self.templates.values() if t.tenant_id == tenant_id]
        if env:
            results = [t for t in results if t.env == env]
        if tag:
            results = [t for t in results if tag in (t.tags or [])]
        return results

    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        return self.templates.get(template_id)

    def delete_template(self, template_id: str) -> None:
        self.templates.pop(template_id, None)


class FirestorePresetRepository(PresetRepository):
    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        project = runtime_config.get_firestore_project()
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _col(self, tenant_id: str, name: str):
        return self._client.collection(f"{name}_{tenant_id}")

    def create_filter(self, preset: FilterPreset) -> FilterPreset:
        self._col(preset.tenant_id, "video_filter_presets").document(preset.id).set(preset.model_dump())
        return preset

    def list_filters(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[FilterPreset]:
        docs = self._col(tenant_id, "video_filter_presets").where("tenant_id", "==", tenant_id).stream()
        results = [FilterPreset(**d.to_dict()) for d in docs]
        if env:
            results = [p for p in results if p.env == env]
        if tag:
            results = [p for p in results if tag in (p.tags or [])]
        return results

    def get_filter(self, preset_id: str) -> Optional[FilterPreset]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_filter_presets").document(preset_id).get()
        return FilterPreset(**snap.to_dict()) if snap and snap.exists else None

    def delete_filter(self, preset_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_filter_presets").document(preset_id).delete()

    def create_motion(self, preset: MotionPreset) -> MotionPreset:
        self._col(preset.tenant_id, "video_motion_presets").document(preset.id).set(preset.model_dump())
        return preset

    def list_motion(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[MotionPreset]:
        docs = self._col(tenant_id, "video_motion_presets").where("tenant_id", "==", tenant_id).stream()
        results = [MotionPreset(**d.to_dict()) for d in docs]
        if env:
            results = [p for p in results if p.env == env]
        if tag:
            results = [p for p in results if tag in (p.tags or [])]
        return results

    def get_motion(self, preset_id: str) -> Optional[MotionPreset]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_motion_presets").document(preset_id).get()
        return MotionPreset(**snap.to_dict()) if snap and snap.exists else None

    def delete_motion(self, preset_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_motion_presets").document(preset_id).delete()

    def create_template(self, template: VideoTemplate) -> VideoTemplate:
        self._col(template.tenant_id, "video_templates").document(template.id).set(template.model_dump())
        return template

    def list_templates(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[VideoTemplate]:
        docs = self._col(tenant_id, "video_templates").where("tenant_id", "==", tenant_id).stream()
        results = [VideoTemplate(**d.to_dict()) for d in docs]
        if env:
            results = [t for t in results if t.env == env]
        if tag:
            results = [t for t in results if tag in (t.tags or [])]
        return results

    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant, "video_templates").document(template_id).get()
        return VideoTemplate(**snap.to_dict()) if snap and snap.exists else None

    def delete_template(self, template_id: str) -> None:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return
        self._col(tenant, "video_templates").document(template_id).delete()

def _built_in_filter_presets() -> List[FilterPreset]:
    presets = []
    
    # Beauty: Teeth
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="beauty_teeth_mild",
        description="Mild teeth whitening",
        filters=[Filter(type="teeth_whiten", params={"intensity": 0.3})],
        tags=["beauty", "built_in"]
    ))
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="beauty_teeth_strong",
        description="Strong teeth whitening",
        filters=[Filter(type="teeth_whiten", params={"intensity": 0.8})],
        tags=["beauty", "built_in"]
    ))
    
    # Beauty: Skin
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="beauty_skin_smooth",
        description="Standard skin smoothing",
        filters=[Filter(type="skin_smooth", params={"intensity": 0.5})],
        tags=["beauty", "built_in"]
    ))

    # Anonymisation: Face
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="anonymise_faces_strong",
        description="Strong face blur for anonymity",
        filters=[Filter(type="face_blur", params={"strength": 1.0})],
        tags=["privacy", "built_in"]
    ))
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="anonymise_faces_medium",
        description="Medium face blur",
        filters=[Filter(type="face_blur", params={"strength": 0.6})],
        tags=["privacy", "built_in"]
    ))
    
    # Style Packs
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="style_cinematic",
        description="Cinematic contrast, vignette, and gentle hue shift",
        filters=[
            Filter(type="contrast", params={"amount": 0.25}),
            Filter(type="gamma", params={"gamma": 0.95}),
            Filter(type="vignette", params={"angle": 0.35, "softness": 0.5, "strength": 0.4}),
            Filter(type="hue_shift", params={"shift": -5}),
            Filter(type="levels", params={"black": 0.03, "white": 0.92, "gamma": 1.0}),
        ],
        tags=["style", "built_in", "cinematic"],
        meta={"render_profiles": ["social_1080p_h264", "youtube_4k_h264"]}
    ))
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="style_vlog",
        description="Bright, punchy vlog-ready grade with glow",
        filters=[
            Filter(type="exposure", params={"stops": 0.1}),
            Filter(type="contrast", params={"amount": 0.15}),
            Filter(type="saturation", params={"amount": 0.25}),
            Filter(type="sharpen", params={"luma_amount": 0.65}),
            Filter(type="bloom", params={"intensity": 0.35}),
        ],
        tags=["style", "built_in", "vlog"],
        meta={"render_profiles": ["preview_720p_fast", "draft_480p_fast"]}
    ))
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="style_punchy",
        description="High contrast, grain, and punchy saturation",
        filters=[
            Filter(type="contrast", params={"amount": 0.35}),
            Filter(type="saturation", params={"amount": 0.45}),
            Filter(type="film_grain", params={"strength": 15}),
        ],
        tags=["style", "built_in", "punchy"],
        meta={"render_profiles": ["social_1080p_h264", "1080p_30_web"]}
    ))
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="style_monochrome",
        description="Rich monochrome grade with controlled curves",
        filters=[
            Filter(type="saturation", params={"amount": -1.0}),
            Filter(type="contrast", params={"amount": 0.2}),
            Filter(type="levels", params={"black": 0.05, "white": 0.95, "gamma": 1.1}),
        ],
        tags=["style", "built_in", "monochrome"],
        meta={"render_profiles": ["social_1080p_h264", "master_4k_prores"]}
    ))

    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="style_documentary",
        description="Soft contrast with cooler tones",
        filters=[
            Filter(type="contrast", params={"amount": 0.15}),
            Filter(type="temperature", params={"shift": -0.15}),
            Filter(type="vignette", params={"angle": 0.4, "softness": 0.6, "strength": 0.35}),
            Filter(type="gamma", params={"gamma": 0.95}),
        ],
        tags=["style", "built_in", "cinematic"],
        meta={"render_profiles": ["social_1080p_h264", "youtube_4k_h264"]}
    ))
    presets.append(FilterPreset(
        tenant_id="built_in", env="global", name="style_neon_punch",
        description="Electric punch with saturation and glow",
        filters=[
            Filter(type="saturation", params={"amount": 0.6}),
            Filter(type="gamma", params={"gamma": 1.1}),
            Filter(type="bloom", params={"intensity": 0.4}),
            Filter(type="hue_shift", params={"shift": 15}),
        ],
        tags=["style", "built_in", "punchy"],
        meta={"render_profiles": ["preview_720p_fast", "draft_480p_fast"]}
    ))

    profile_defaults: Dict[str, List[Filter]] = {
        "social_1080p_h264": [
            Filter(type="levels", params={"black": 0.02, "white": 0.96, "gamma": 1.0}),
            Filter(type="contrast", params={"amount": 0.12}),
        ],
        "preview_720p_fast": [
            Filter(type="gamma", params={"gamma": 1.05}),
            Filter(type="sharpen", params={"luma_amount": 0.4}),
        ],
        "youtube_4k_h264": [
            Filter(type="levels", params={"black": 0.03, "white": 0.98, "gamma": 0.98}),
            Filter(type="bloom", params={"intensity": 0.28}),
        ],
        "master_4k_prores": [
            Filter(type="levels", params={"black": 0.01, "white": 0.99, "gamma": 1.0}),
            Filter(type="vignette", params={"angle": 0.25, "softness": 0.4, "strength": 0.3}),
        ],
        "1080p_30_web": [
            Filter(type="contrast", params={"amount": 0.15}),
            Filter(type="film_grain", params={"strength": 8}),
        ],
        "draft_480p_fast": [
            Filter(type="exposure", params={"stops": 0.05}),
            Filter(type="sharpen", params={"luma_amount": 0.35}),
        ],
    }
    for profile_name, filters in profile_defaults.items():
        presets.append(FilterPreset(
            tenant_id="built_in",
            env="global",
            name=f"profile_default_{profile_name}",
            description=f"Default tweak for {profile_name}",
            filters=filters,
            tags=["profile_default", "built_in", "render_profile"],
            meta={"render_profiles": [profile_name]},
        ))

    return presets



def _shake_keyframes(amplitude: float, duration_ms: int, axis: str) -> List[Keyframe]:
    steps = [0, duration_ms // 4, duration_ms // 2, (duration_ms * 3) // 4, duration_ms]
    signs = [1, -1, 1, -1, 0]
    return [Keyframe(time_ms=t, value=0.5 + s * amplitude, interpolation="linear") for t, s in zip(steps, signs)]


def _built_in_motion_presets() -> List[MotionPreset]:
    presets: List[MotionPreset] = []
    amps = [0.02, 0.04, 0.06]
    for idx, amp in enumerate(amps, start=1):
        duration = 800 if idx == 1 else 600
        kf_x = _shake_keyframes(amp, duration, "x")
        kf_y = _shake_keyframes(amp, duration, "y")
        tracks = [
            ParameterAutomation(
                tenant_id="built_in",
                env="global",
                target_type="clip",
                target_id="",
                property="position_x",
                keyframes=kf_x,
            ),
            ParameterAutomation(
                tenant_id="built_in",
                env="global",
                target_type="clip",
                target_id="",
                property="position_y",
                keyframes=kf_y,
            ),
        ]
        presets.append(
            MotionPreset(
                tenant_id="built_in",
                env="global",
                name=f"shake_{idx}",
                description=f"Built-in shake preset {idx}",
                duration_ms=duration,
                tracks=tracks,
                tags=["shake", "built_in"],
                meta={"built_in": True},
            )
        )
    presets.append(_build_pan_preset(1200))
    presets.append(_build_pan_preset(1800))
    zoom_keyframes = _gentle_zoom_keyframes(1400)
    presets.append(
        MotionPreset(
            tenant_id="built_in",
            env="global",
            name="gentle_zoom",
            description="Subtle zoom for cinematic emphasis",
            duration_ms=1400,
            tracks=[
                ParameterAutomation(
                    tenant_id="built_in",
                    env="global",
                    target_type="clip",
                    target_id="",
                    property="scale",
                    keyframes=zoom_keyframes,
                )
            ],
            tags=["zoom", "built_in", "cinematic"],
            meta={"render_profiles": ["social_1080p_h264", "youtube_4k_h264"]},
        )
    )
    
    # Micro-Animations
    for dur in [500, 1000]:
        presets.append(MotionPreset(tenant_id="built_in", env="global", name=f"pop_{dur}", description=f"Pop in over {dur}ms", duration_ms=dur, tracks=[
            ParameterAutomation(tenant_id="built_in", env="global", target_type="clip", target_id="", property="scale", keyframes=_pop_keyframes(dur))
        ], tags=["pop", "built_in"]))
        
        presets.append(MotionPreset(tenant_id="built_in", env="global", name=f"pulse_{dur}", description=f"Pulse scale over {dur}ms", duration_ms=dur, tracks=[
            ParameterAutomation(tenant_id="built_in", env="global", target_type="clip", target_id="", property="scale", keyframes=_pulse_keyframes(dur))
        ], tags=["pulse", "built_in"]))

        presets.append(MotionPreset(tenant_id="built_in", env="global", name=f"zoom_in_{dur}", description=f"Zoom in 20% over {dur}ms", duration_ms=dur, tracks=[
            ParameterAutomation(tenant_id="built_in", env="global", target_type="clip", target_id="", property="scale", keyframes=_zoom_in_keyframes(dur))
        ], tags=["zoom", "built_in"]))

    return presets


def _built_in_templates() -> List[VideoTemplate]:
    templates = []
    
    # Vlog 4:3
    templates.append(VideoTemplate(
        tenant_id="built_in",
        env="global",
        name="vlog_4_3",
        description="4:3 Vlog style with moderate shake and punchy look",
        render_profile="social_4_3_h264",
        filter_preset_id="style_vlog",
        motion_preset_id="shake_1",
        tags=["vlog", "social", "4:3", "built_in"]
    ))
    
    # Social 1:1
    templates.append(VideoTemplate(
        tenant_id="built_in",
        env="global",
        name="social_square_punchy",
        description="Square 1:1 format with high contrast and pop animation",
        render_profile="social_1_1_h264",
        filter_preset_id="style_punchy",
        motion_preset_id="pop_500",
        tags=["social", "square", "1:1", "built_in"]
    ))

    # Cinematic Landscape
    templates.append(VideoTemplate(
        tenant_id="built_in",
        env="global",
        name="cinematic_pan",
        description="Cinematic look with slow pan",
        render_profile="social_1080p_h264",
        filter_preset_id="style_cinematic",
        motion_preset_id="steady_pan_1800",
        tags=["cinematic", "landscape", "built_in"]
    ))
    return templates


def _gentle_pan_keyframes(duration_ms: int, axis: str) -> List[Keyframe]:
    steps = [0, duration_ms // 2, duration_ms]
    values = [0.45, 0.5, 0.55] if axis == "x" else [0.5, 0.55, 0.5]
    return [Keyframe(time_ms=t, value=v, interpolation="ease_in_out") for t, v in zip(steps, values)]



def _gentle_zoom_keyframes(duration_ms: int) -> List[Keyframe]:
    steps = [0, duration_ms // 2, duration_ms]
    values = [0.97, 1.0, 1.03]
    return [Keyframe(time_ms=t, value=v, interpolation="ease_in_out") for t, v in zip(steps, values)]


def _pop_keyframes(duration_ms: int) -> List[Keyframe]:
    # 0 -> 1.1 -> 1.0 (overshoot)
    steps = [0, int(duration_ms * 0.7), duration_ms]
    values = [0.0, 1.1, 1.0]
    return [Keyframe(time_ms=t, value=v, interpolation="ease_out") for t, v in zip(steps, values)]


def _pulse_keyframes(duration_ms: int) -> List[Keyframe]:
    # 1.0 -> 1.1 -> 1.0
    steps = [0, duration_ms // 2, duration_ms]
    values = [1.0, 1.1, 1.0]
    return [Keyframe(time_ms=t, value=v, interpolation="ease_in_out") for t, v in zip(steps, values)]


def _slide_keyframes(duration_ms: int, direction: str) -> List[Keyframe]:
    # 0 -> 1 (progress)? No, actual position values.
    # Assuming normalized coordinates 0-1? Or arbitrary?
    # Position automation usually depends on canvas size, but if normalized (0.0-1.0):
    # Slide In: offscreen to center.
    # Slide Out: center to offscreen.
    # "Slide" generic: usually translation.
    # Let's assume "Slide Entry" (offscreen to position).
    # If x: -0.5 -> 0.0 (assuming relative or absolute?)
    # Timeline model has position: Optional[dict] = None # {"x":..., "y":...}
    # If we automate "position_x", likely it's relative offset or absolute?
    # Usually absolute normalized or pixels?
    # Let's assume "slide" is a small movement for emphasis, not entry/exit.
    # "Slide": move slightly.
    start = 0.0
    end = 0.2 if direction in ("right", "down") else -0.2
    return [Keyframe(time_ms=0, value=start, interpolation="ease_in_out"), Keyframe(time_ms=duration_ms, value=end, interpolation="linear")]


def _zoom_in_keyframes(duration_ms: int) -> List[Keyframe]:
    return [Keyframe(time_ms=0, value=1.0, interpolation="linear"), Keyframe(time_ms=duration_ms, value=1.2, interpolation="linear")]


def _build_pan_preset(duration_ms: int) -> MotionPreset:
    return MotionPreset(
        tenant_id="built_in",
        env="global",
        name=f"steady_pan_{duration_ms}",
        description=f"Gentle pan over {duration_ms}ms",
        duration_ms=duration_ms,
        tracks=[
            ParameterAutomation(
                tenant_id="built_in",
                env="global",
                target_type="clip",
                target_id="",
                property="position_x",
                keyframes=_gentle_pan_keyframes(duration_ms, "x"),
            ),
            ParameterAutomation(
                tenant_id="built_in",
                env="global",
                target_type="clip",
                target_id="",
                property="position_y",
                keyframes=_gentle_pan_keyframes(duration_ms, "y"),
            ),
        ],
        tags=["pan", "built_in"],
        meta={"render_profiles": ["social_1080p_h264", "preview_720p_fast"]},
    )


class PresetService:
    def __init__(self, repo: Optional[PresetRepository] = None) -> None:
        self.repo = repo or self._default_repo()
        self._built_in_motion = _built_in_motion_presets()
        self._built_in_filters = _built_in_filter_presets()
        self._built_in_templates = _built_in_templates()

    def _default_repo(self) -> PresetRepository:
        try:
            return FirestorePresetRepository()
        except Exception:
            return InMemoryPresetRepository()

    # Filter presets
    def create_filter_preset(self, preset: FilterPreset) -> FilterPreset:
        return self.repo.create_filter(preset)

    def list_filter_presets(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[FilterPreset]:
        user_presets = self.repo.list_filters(tenant_id, env=env, tag=tag)
        built_ins = [p for p in self._built_in_filters if (not tag or tag in (p.tags or []))]
        return built_ins + user_presets

    def get_filter_preset(self, preset_id: str) -> Optional[FilterPreset]:
        preset = self.repo.get_filter(preset_id)
        if preset:
            return preset
        for p in self._built_in_filters:
            if p.id == preset_id or p.name == preset_id:
                return p
        return None

    def delete_filter_preset(self, preset_id: str) -> None:
        self.repo.delete_filter(preset_id)

    # Motion presets
    def create_motion_preset(self, preset: MotionPreset) -> MotionPreset:
        return self.repo.create_motion(preset)

    def list_motion_presets(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[MotionPreset]:
        user_presets = self.repo.list_motion(tenant_id, env=env, tag=tag)
        built_ins = [p for p in self._built_in_motion if (not tag or tag in (p.tags or []))]
        return built_ins + user_presets

    def get_motion_preset(self, preset_id: str) -> Optional[MotionPreset]:
        preset = self.repo.get_motion(preset_id)
        if preset:
            return preset
        for p in self._built_in_motion:
            if p.id == preset_id or p.name == preset_id:
                return p
        return None

    def delete_motion_preset(self, preset_id: str) -> None:
        self.repo.delete_motion(preset_id)

    # Templates
    def create_template(self, template: VideoTemplate) -> VideoTemplate:
        return self.repo.create_template(template)

    def list_templates(self, tenant_id: str, env: Optional[str] = None, tag: Optional[str] = None) -> List[VideoTemplate]:
        user_templates = self.repo.list_templates(tenant_id, env=env, tag=tag)
        built_ins = [t for t in self._built_in_templates if (not tag or tag in (t.tags or []))]
        return built_ins + user_templates

    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        template = self.repo.get_template(template_id)
        if template:
            return template
        for t in self._built_in_templates:
            if t.id == template_id or t.name == template_id:
                return t
        return None

    def delete_template(self, template_id: str) -> None:
        self.repo.delete_template(template_id)


_default_service: Optional[PresetService] = None


def get_preset_service() -> PresetService:
    global _default_service
    if _default_service is None:
        _default_service = PresetService()
    return _default_service


def set_preset_service(service: PresetService) -> None:
    global _default_service
    _default_service = service
