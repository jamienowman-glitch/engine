from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

from engines.video_timeline.models import Clip, Transition

_TRANSITION_CATALOG: Dict[str, Dict[str, str]] = {
    "crossfade": {"xfade": "fade", "audio": "acrossfade"},
    "dip_to_black": {"xfade": "fadeblack", "audio": "acrossfade"},
    "dip_to_white": {"xfade": "fadewhite", "audio": "acrossfade"},
    "wipe_left": {"xfade": "wipeleft", "audio": "acrossfade"},
    "wipe_right": {"xfade": "wiperight", "audio": "acrossfade"},
    "push_left": {"xfade": "slideleft", "audio": "acrossfade"},
    "push_right": {"xfade": "slideright", "audio": "acrossfade"},
    "slide_up": {"xfade": "slideup", "audio": "acrossfade"},
    "slide_down": {"xfade": "slidedown", "audio": "acrossfade"},
}


TRANSITION_PRESETS: Dict[str, Dict[str, object]] = {
    "quick_crossfade": {"type": "crossfade", "duration_ms": 250},
    "standard_crossfade": {"type": "crossfade", "duration_ms": 500},
    "slow_crossfade": {"type": "crossfade", "duration_ms": 1000},
    "dip_black": {"type": "dip_to_black", "duration_ms": 400},
    "dip_white": {"type": "dip_to_white", "duration_ms": 400},
    "wipes_left": {"type": "wipe_left", "duration_ms": 600},
    "wipes_right": {"type": "wipe_right", "duration_ms": 600},
    "slide_entry": {"type": "push_left", "duration_ms": 500},
}


def _clip_timeline_duration_ms(clip: Optional[Clip]) -> float:
    if not clip:
        return 0.0
    base = max(0.0, clip.out_ms - clip.in_ms)
    speed = clip.speed if getattr(clip, "speed", 1.0) else 1.0
    return base / speed if speed > 0 else base


def _transition_start_ms(transition: Transition, clips: Mapping[str, Clip], duration_ms: float) -> float:
    from_clip = clips.get(transition.from_clip_id)
    to_clip = clips.get(transition.to_clip_id)
    candidate = 0.0
    if from_clip and to_clip:
        candidate = min(
            max(to_clip.start_ms_on_timeline - duration_ms, from_clip.start_ms_on_timeline),
            from_clip.start_ms_on_timeline + _clip_timeline_duration_ms(from_clip),
        )
    elif from_clip:
        candidate = max(from_clip.start_ms_on_timeline + _clip_timeline_duration_ms(from_clip) - duration_ms, from_clip.start_ms_on_timeline)
    elif to_clip:
        candidate = max(to_clip.start_ms_on_timeline - duration_ms, 0.0)
    return max(0.0, candidate)


@dataclass
class TransitionPlan:
    transition_id: str
    type: str
    from_clip_id: str
    to_clip_id: str
    duration_ms: float
    start_ms: float
    order: int
    video_filter: str
    audio_filter: str
    video_alias: str
    audio_alias: str
    preset_id: Optional[str] = None

    def to_meta(self) -> Dict[str, object]:
        return {
            "id": self.transition_id,
            "type": self.type,
            "from_clip_id": self.from_clip_id,
            "to_clip_id": self.to_clip_id,
            "duration_ms": self.duration_ms,
            "start_ms": self.start_ms,
            "order": self.order,
            "video_alias": self.video_alias,
            "audio_alias": self.audio_alias,
            "preset_id": self.preset_id,
        }


def build_transition_plans(transitions: Iterable[Transition], clips: Mapping[str, Clip]) -> List[TransitionPlan]:
    raw_plans: List[TransitionPlan] = []
    for transition in transitions:
        t_type = transition.type
        t_duration = transition.duration_ms
        preset_id = transition.meta.get("preset_id")
        
        # Resolve preset from meta if present
        if preset_id and preset_id in TRANSITION_PRESETS:
            preset = TRANSITION_PRESETS[preset_id]
            # Validate consistency (optional, but helpful)
            if str(preset["type"]) != t_type:
                # If types conflict, we could warn, or let preset override?
                # But since we base 'mapping' on t_type later, we should update t_type OR ensure they match.
                # Planner's job is to build the graph. If preset implies a differnt ffmpeg filter, we should use preset's type.
                # However, catalog lookup relies on t_type.
                 t_type = str(preset["type"])
            
            if t_duration is None or t_duration <= 0:
                t_duration = float(preset["duration_ms"])
        
        if t_type == "none" or (t_duration is not None and t_duration <= 0):
            continue
            
        mapping = _TRANSITION_CATALOG.get(t_type)
        if not mapping:
            # Fallback or strict error
            raise ValueError(f"Unsupported transition type: {t_type}")

        duration_ms = max(1.0, float(t_duration) if t_duration is not None else 500.0) # Default 500ms fallback
        from_clip = clips.get(transition.from_clip_id)
        to_clip = clips.get(transition.to_clip_id)
        for clip in (from_clip, to_clip):
            clip_len = _clip_timeline_duration_ms(clip)
            if clip_len > 0:
                duration_ms = min(duration_ms, clip_len)
        duration_sec = duration_ms / 1000.0
        start_ms = _transition_start_ms(transition, clips, duration_ms)
        video_filter = f"xfade=transition={mapping['xfade']}:duration={duration_sec:.3f}:offset=0"
        audio_filter = f"{mapping['audio']}=d={duration_sec:.3f}"
        plan = TransitionPlan(
            transition_id=transition.id,
            type=t_type,
            from_clip_id=transition.from_clip_id,
            to_clip_id=transition.to_clip_id,
            duration_ms=duration_ms,
            start_ms=start_ms,
            order=0,
            video_filter=video_filter,
            audio_filter=audio_filter,
            video_alias=mapping["xfade"],
            audio_alias=mapping["audio"],
            preset_id=preset_id,
        )
        raw_plans.append(plan)

    sorted_plans = sorted(raw_plans, key=lambda plan: (plan.start_ms, plan.transition_id))
    for idx, plan in enumerate(sorted_plans):
        plan.order = idx
    return sorted_plans
