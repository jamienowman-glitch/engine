from __future__ import annotations
from typing import Optional, List, Dict, Any

from engines.audio_arrangement_engine.models import ArrangementRequest, ArrangementResult, ArrangementTemplate
from engines.audio_arrangement_engine.templates import STRUCTURE_TEMPLATES
from engines.audio_timeline.service import get_audio_timeline_service
from engines.audio_timeline.models import SectionMarker

class AudioArrangementEngineService:
    def generate_arrangement(self, req: ArrangementRequest) -> ArrangementResult:
        if req.template_id not in STRUCTURE_TEMPLATES:
            raise ValueError(f"Unknown template: {req.template_id}")
            
        tmpl = STRUCTURE_TEMPLATES[req.template_id]
        
        tl_svc = get_audio_timeline_service()
        seq = tl_svc.create_sequence(req.tenant_id, req.env, bpm=req.bpm)
        
        # 1. Identify Roles from Request
        request_roles = set(req.pattern_clips_by_role.keys())
        template_roles = {
            role for section in tmpl.sections for role in section.active_roles
        }
        extra_roles = request_roles - template_roles
        if extra_roles:
            raise ValueError(f"Unknown roles for template {tmpl.id}: {sorted(extra_roles)}")

        roles = list(request_roles)
        tracks_by_role = {}
        for role in roles:
            tracks_by_role[role] = tl_svc.add_track(seq, name=role.capitalize(), role=role, meta={"role": role})
            
        # 2. Arrange
        ms_per_beat = 60000.0 / req.bpm
        ms_per_bar = ms_per_beat * 4 # Assuming 4/4
        
        current_ms = 0.0
        
        for section in tmpl.sections:
            # Add Marker
            seq.markers.append(SectionMarker(
                start_ms=current_ms,
                name=section.name,
                duration_bars=section.bars
            ))
            
            # Place Clips for Section Duration
            section_duration_ms = section.bars * ms_per_bar
            
            # We iterate bar by bar to keep pattern alignment
            for bar_i in range(section.bars):
                bar_start_ms = current_ms + (bar_i * ms_per_bar)
                
                for role in section.active_roles:
                    # Find track (case insensitive matching?)
                    # Simplification: use exact role map key
                    
                    # If role specified in template but not in request, skip
                    if role not in req.pattern_clips_by_role:
                        continue
                        
                    track = tracks_by_role.get(role)
                    if not track: continue # Should exist if in pattern_clips keys
                    
                    clips_data = req.pattern_clips_by_role[role]
                    
                    for clip_dict in clips_data:
                        # clip_dict start_ms is relative to pattern start (0..bar_duration)
                        # We place it relative to bar_start_ms
                        
                        abs_start = bar_start_ms + clip_dict["start_ms"]
                        
                        tl_svc.add_clip(
                            track,
                            start_ms=abs_start,
                            asset_id=clip_dict.get("asset_id"),
                            artifact_id=clip_dict.get("artifact_id"),
                            duration_ms=clip_dict.get("duration_ms", 500.0),
                            source_offset_ms=clip_dict.get("source_offset_ms", 0.0),
                            gain_db=clip_dict.get("gain_db", 0.0)
                        )
                        
            current_ms += section_duration_ms
            
        seq.duration_ms = current_ms
        
        return ArrangementResult(
            sequence=seq,
            meta={"bars": current_ms / ms_per_bar, "template": req.template_id}
        )

_default_service: Optional[AudioArrangementEngineService] = None

def get_audio_arrangement_engine_service() -> AudioArrangementEngineService:
    global _default_service
    if _default_service is None:
        _default_service = AudioArrangementEngineService()
    return _default_service
