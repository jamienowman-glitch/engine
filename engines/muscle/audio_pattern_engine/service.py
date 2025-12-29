from __future__ import annotations

from typing import Optional, List, Dict, Any
import math

from engines.audio_pattern_engine.models import PatternRequest, PatternResult, PatternTemplate
from engines.audio_pattern_engine.templates import TEMPLATES
from engines.audio_groove.service import get_audio_groove_service

class AudioPatternEngineService:
    def generate_pattern(self, req: PatternRequest) -> PatternResult:
        # 1. Load Template
        if req.template_id not in TEMPLATES:
            raise ValueError(f"Unknown template: {req.template_id}")
        
        tmpl = TEMPLATES[req.template_id]
        
        # 2. BPM and Swing
        bpm = req.bpm if req.bpm is not None else tmpl.bpm_default
        swing_pct = req.swing_pct if req.swing_pct is not None else tmpl.swing_default
        
        # Groove Profile
        groove_offsets = None
        if req.groove_profile_id:
            try:
                g_svc = get_audio_groove_service()
                profile = g_svc.get_groove_profile(req.groove_profile_id)
                if profile:
                    # Check compatibility (subdivision?)
                    if profile.subdivision == 16:
                        groove_offsets = profile.offsets
            except Exception:
                pass # Fail safe to straight
        
        # 3. Time Calculations
        # 1 beat = 60000 / bpm ms
        # 1 bar (4/4) = 4 beats
        # 16th note = beat / 4
        
        ms_per_beat = 60000.0 / bpm
        ms_per_16th = ms_per_beat / 4.0
        
        # Swing offset: 
        # Usually applied to even numbered 16ths (0, 1, 2, 3...) -> 1, 3, 5 are off-beats.
        # With 0-based index: 0 is on-beat, 1 is off-beat (e.g. 1e&a -> 1 is 'e', 2 is '&', 3 is 'a'?)
        # Standard swing pairs: (Step 0, Step 1). Step 0 is fixed. Step 1 is delayed.
        # Delay amount: If swing=50 (neutral), offset=0.
        # If swing=66 (triplet), offset = ...
        # Standard MPC swing: pct ranges 50 to 75. 
        # Formula: offset = (swing_pct - 50) / 50 * (ms_per_16th / ) ?
        # Simpler: 
        # Max delay is usually moving strictly towards triplet or next 8th.
        # Let's map swing_pct (0-100) to actual offset. 
        # If 0 (straight): offset 0.
        # If we use simple formula: offset = (swing_pct / 100.0) * ms_per_16th * 0.66 (arbitrary feel factor?)
        # Let's assume input swing is percentage of a 16th note duration to shift?
        # Or typical 50-75 scale.
        # Let's implement generic: swing_pct 0 = straight. 100 = hard swing (dotted 8th + 16th feel?)
        # Generic swing delay: offset = (swing_pct / 100.0) * (ms_per_16th / 1.5)
        
        swing_offset_ms = 0.0
        if swing_pct > 0:
            swing_offset_ms = (swing_pct / 100.0) * (ms_per_16th * 0.5) 
        
        result_clips = []
        
        # 4. Iterate Tracks
        for track in tmpl.tracks:
            # Resolve Artifact ID
            art_id = req.sample_map.get(track.role)
            if not art_id:
                # Missing sample for role, skip track
                continue
                
            step_count = len(track.steps)
            if step_count == 0: continue
            
            # Duration of pattern in steps? usually 16.
            # If template says bars=1, we assume steps cover that or loop.
            
            for step_idx, velocity in enumerate(track.steps):
                if velocity <= 0.0:
                    continue
                
                # Base time
                start_ms = step_idx * ms_per_16th
                
                # Apply Swing OR Groove
                if groove_offsets and step_idx < len(groove_offsets):
                     start_ms += groove_offsets[step_idx]
                elif step_idx % 2 == 1:
                    # Fallback to swing if no groove profile
                    start_ms += swing_offset_ms
                
                # Velocity to Gain DB
                # vel 1.0 = 0 dB. 0.0 = -inf.
                # gain = 20 * log10(vel)
                if velocity >= 1.0:
                    gain_db = 0.0
                elif velocity < 0.01:
                    gain_db = -60.0
                else:
                    gain_db = 20.0 * math.log10(velocity)
                
                clip = {
                    "asset_id": None,
                    "artifact_id": art_id,
                    "start_ms": float(start_ms),
                    "duration_ms": 500.0, # Default duration, render engine might trim or play full
                    "source_offset_ms": 0.0,
                    "gain_db": float(gain_db),
                    "label": f"{track.role}_{step_idx}"
                }
                result_clips.append(clip)
                
        return PatternResult(
            clips=result_clips,
            meta={
                "bpm": bpm,
                "swing_pct": swing_pct,
                "template_id": req.template_id
            }
        )

_default_service: Optional[AudioPatternEngineService] = None

def get_audio_pattern_engine_service() -> AudioPatternEngineService:
    global _default_service
    if _default_service is None:
        _default_service = AudioPatternEngineService()
    return _default_service
