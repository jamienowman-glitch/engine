from typing import List, Optional
from engines.audio_performance_capture.models import PerformanceEvent
from engines.audio_groove.models import GrooveProfile

def quantise_events(
    events: List[PerformanceEvent], 
    bpm: float, 
    subdivision: int = 16,
    groove_profile: Optional[GrooveProfile] = None,
    humanise_blend: float = 0.0
) -> List[PerformanceEvent]:
    
    if not events:
        return []
        
    ms_per_beat = 60000.0 / bpm
    steps_per_beat = subdivision / 4.0 # e.g. 16th -> 4 steps per beat
    ms_per_step = ms_per_beat / steps_per_beat
    
    quantised = []
    
    for evt in events:
        original = evt.time_ms
        
        # 1. Find nearest grid step
        # Step index (continuous)
        step_idx_float = original / ms_per_step
        step_idx = round(step_idx_float)
        
        # 2. Calculate Grid Time
        grid_time = step_idx * ms_per_step
        
        # 3. Apply Groove
        # Groove offsets are defined per step in a bar (0..subdivision-1)
        groove_offset = 0.0
        if groove_profile:
            # step within bar
            bar_step = step_idx % groove_profile.subdivision
            if bar_step < len(groove_profile.offsets):
                groove_offset = groove_profile.offsets[bar_step]
                
        target_time = grid_time + groove_offset
        
        # 4. Humanise Blend
        # 0.0 = Target. 1.0 = Original.
        final_time = (target_time * (1.0 - humanise_blend)) + (original * humanise_blend)
        
        # Update event
        # Create new instance
        new_evt = evt.model_copy()
        new_evt.time_ms = final_time
        quantised.append(new_evt)
        
    return quantised
