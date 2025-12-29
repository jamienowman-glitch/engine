from __future__ import annotations
from typing import Optional, List, Any
import copy

from engines.audio_structure_engine.models import ArrangementRequest, ArrangementResult, StructureTemplate
from engines.audio_structure_engine.templates import STRUCTURE_TEMPLATES
from engines.audio_timeline.service import get_audio_timeline_service
from engines.audio_timeline.models import AudioSequence, AudioTrack, AudioClip, SectionMarker

class AudioStructureEngineService:
    def arrange_song(self, req: ArrangementRequest) -> ArrangementResult:
        if req.template_id not in STRUCTURE_TEMPLATES:
            raise ValueError(f"Unknown template: {req.template_id}")
            
        tmpl = STRUCTURE_TEMPLATES[req.template_id]
        
        tl_service = get_audio_timeline_service()
        seq = tl_service.create_sequence(req.tenant_id, req.env, bpm=req.bpm)
        
        # Validate role mapping vs template
        request_roles = set(req.pattern_clips_by_role.keys())
        template_roles = {
            role for section in tmpl.sections for role in section.active_roles
        }
        extra_roles = request_roles - template_roles
        if extra_roles:
            raise ValueError(f"Unknown roles for template {tmpl.id}: {sorted(extra_roles)}")

        # Create tracks for roles
        roles = list(request_roles)
        tracks_by_role = {}
        for role in roles:
            tracks_by_role[role] = tl_service.add_track(seq, name=role.capitalize(), role=role)
            
        # Calculation
        ms_per_beat = 60000.0 / req.bpm
        # Assuming 4/4
        ms_per_bar = ms_per_beat * 4
        
        current_ms = 0.0

        for section in tmpl.sections:
            seq.markers.append(SectionMarker(start_ms=current_ms, name=section.name, duration_bars=section.bars))
            section_duration_ms = section.bars * ms_per_bar

            for bar_i in range(section.bars):
                bar_start_ms = current_ms + (bar_i * ms_per_bar)

                for role in section.active_roles:
                    if role not in tracks_by_role:
                        continue

                    track = tracks_by_role[role]
                    pattern = req.pattern_clips_by_role.get(role, [])

                    for clip_dict in pattern:
                        abs_start = bar_start_ms + clip_dict["start_ms"]
                        tl_service.add_clip(
                            track,
                            start_ms=abs_start,
                            asset_id=clip_dict.get("asset_id"),
                            artifact_id=clip_dict.get("artifact_id"),
                            duration_ms=clip_dict.get("duration_ms", 500.0),
                            source_offset_ms=clip_dict.get("source_offset_ms", 0.0)
                        )

            current_ms += section_duration_ms
        
        seq.duration_ms = current_ms
        
        return ArrangementResult(
            sequence=seq,
            meta={"template_id": req.template_id, "bars": current_ms / ms_per_bar}
        )

_default_service: Optional[AudioStructureEngineService] = None

def get_audio_structure_engine_service() -> AudioStructureEngineService:
    global _default_service
    if _default_service is None:
        _default_service = AudioStructureEngineService()
    return _default_service
