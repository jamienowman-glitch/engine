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
        }


def build_transition_plans(transitions: Iterable[Transition], clips: Mapping[str, Clip]) -> List[TransitionPlan]:
    raw_plans: List[TransitionPlan] = []
    for transition in transitions:
        if transition.type == "none" or transition.duration_ms <= 0:
            continue
        mapping = _TRANSITION_CATALOG.get(transition.type)
        if not mapping:
            raise ValueError(f"Unsupported transition type: {transition.type}")
        duration_ms = max(1.0, float(transition.duration_ms))
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
            type=transition.type,
            from_clip_id=transition.from_clip_id,
            to_clip_id=transition.to_clip_id,
            duration_ms=duration_ms,
            start_ms=start_ms,
            order=0,
            video_filter=video_filter,
            audio_filter=audio_filter,
            video_alias=mapping["xfade"],
            audio_alias=mapping["audio"],
        )
        raw_plans.append(plan)

    sorted_plans = sorted(raw_plans, key=lambda plan: (plan.start_ms, plan.transition_id))
    for idx, plan in enumerate(sorted_plans):
        plan.order = idx
    return sorted_plans
