from __future__ import annotations
from typing import Optional, List, Dict, Any, Sequence
from engines.audio_timeline.models import AudioSequence, AudioTrack, AudioClip, AudioProject, AutomationPoint

class AudioTimelineService:
    def create_sequence(self, tenant_id: str, env: str, bpm: float = 120.0) -> AudioSequence:
        return AudioSequence(tenant_id=tenant_id, env=env, bpm=bpm)
        
    def add_track(self, sequence: AudioSequence, name: str = "Audio Track", role: str = "music", meta: Dict[str, Any] = None) -> AudioTrack:
        track = AudioTrack(name=name, order=len(sequence.tracks), meta=meta or {}, role=role)
        if role:
            track.meta["role"] = role
        sequence.tracks.append(track)
        return track
        
    def add_clip(self, track: AudioTrack, 
                 start_ms: float, 
                 asset_id: Optional[str] = None, 
                 artifact_id: Optional[str] = None,
                 duration_ms: float = 1000.0,
                 source_offset_ms: float = 0.0,
                 gain_db: float = 0.0,
                 fade_in_ms: float = 0.0,
                 fade_out_ms: float = 0.0,
                 fade_curve: str = "tri",
                 crossfade_in_ms: float = 0.0,
                 crossfade_out_ms: float = 0.0,
                 crossfade_curve: str = "tri"
                 ) -> AudioClip:
                 
        if not asset_id and not artifact_id:
            raise ValueError("Must provide asset_id or artifact_id")
            
        self._validate_fades(duration_ms, fade_in_ms, fade_out_ms, crossfade_in_ms, crossfade_out_ms)

        clip = AudioClip(
            asset_id=asset_id,
            artifact_id=artifact_id,
            start_ms=start_ms,
            duration_ms=duration_ms,
            source_offset_ms=source_offset_ms,
            gain_db=gain_db,
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
            fade_curve=fade_curve,
            crossfade_in_ms=crossfade_in_ms,
            crossfade_out_ms=crossfade_out_ms,
            crossfade_curve=crossfade_curve
        )
        # Validate overlap?
        # For V1 allow overlap (DAW style mixing).
        track.clips.append(clip)
        return clip

    def set_track_role(self, track: AudioTrack, role: str) -> None:
        track.role = role
        track.meta.setdefault("role", role)

    def add_clip_automation(self, clip: AudioClip, param: str, points: Sequence[AutomationPoint]) -> None:
        if not points:
            return
        validated = self._validate_clip_automation(clip, points)
        clip.automation[param] = validated

    def add_track_automation(self, track: AudioTrack, param: str, points: Sequence[AutomationPoint]) -> None:
        if not points:
            return
        validated = self._validate_timeline_automation(points)
        track.automation[param] = validated

    def _validate_fades(self, duration: float, fade_in: float, fade_out: float, cross_in: float, cross_out: float) -> None:
        if fade_in < 0 or fade_out < 0:
            raise ValueError("Fade durations must be non-negative")
        if cross_in < 0 or cross_out < 0:
            raise ValueError("Crossfade durations must be non-negative")
        if fade_in + fade_out > duration:
            raise ValueError("Fade in/out sum cannot exceed clip duration")
        if cross_in + cross_out > duration:
            raise ValueError("Crossfade hints cannot exceed clip duration")

    def _validate_timeline_automation(self, points: Sequence[AutomationPoint]) -> List[AutomationPoint]:
        sorted_points = sorted(points, key=lambda p: p.time_ms)
        seen = set()
        for point in sorted_points:
            if point.time_ms < 0:
                raise ValueError("Automation time must be >= 0")
            if point.time_ms in seen:
                raise ValueError(f"Duplicate automation time detected (t={point.time_ms})")
            seen.add(point.time_ms)
        return sorted_points

    def _validate_clip_automation(self, clip: AudioClip, points: Sequence[AutomationPoint]) -> List[AutomationPoint]:
        sorted_points = self._validate_timeline_automation(points)
        start = clip.start_ms
        end = clip.start_ms + clip.duration_ms
        for point in sorted_points:
            if not (start <= point.time_ms <= end):
                raise ValueError("Automation point outside clip bounds")
        return sorted_points

_default_service: Optional[AudioTimelineService] = None

def get_audio_timeline_service() -> AudioTimelineService:
    global _default_service
    if _default_service is None:
        _default_service = AudioTimelineService()
    return _default_service
