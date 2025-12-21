import numpy as np
from typing import List, Optional

ALLOWED_SUBDIVISIONS = (8, 16, 32)


def _normalize_subdivision(value: int) -> int:
    if value in ALLOWED_SUBDIVISIONS:
        return value
    if value < min(ALLOWED_SUBDIVISIONS):
        return min(ALLOWED_SUBDIVISIONS)
    if value > max(ALLOWED_SUBDIVISIONS):
        return max(ALLOWED_SUBDIVISIONS)
    # Choose closest allowed subdivision
    closest = min(ALLOWED_SUBDIVISIONS, key=lambda x: abs(x - value))
    return closest


def _fill_missing_offsets(raw_avgs: List[Optional[float]]) -> List[float]:
    filled = list(raw_avgs)
    length = len(filled)
    for idx, val in enumerate(filled):
        if val is not None:
            continue
        left = 0.0
        for left_idx in range(idx - 1, -1, -1):
            if filled[left_idx] is not None:
                left = filled[left_idx]
                break
        right = None
        for right_idx in range(idx + 1, length):
            if filled[right_idx] is not None:
                right = filled[right_idx]
                break
        if right is not None:
            filled[idx] = (left + right) / 2.0
        else:
            filled[idx] = left
    return [val if val is not None else 0.0 for val in filled]


def extract_groove_offsets(audio_path: str, bpm: float, subdivision: int = 16) -> List[float]:
    """
    Extracts timing offsets (ms) for each step in a bar (defined by subdivision).
    Positive offset = late (laid back). Negative = early (rushed).
    """
    import librosa
    try:
        y, sr = librosa.load(audio_path, sr=None)
    except Exception:
        # Fallback if librosa fails or file not found (testing/stubs)
        return [0.0] * subdivision

    # 1. Onset Detection
    # onset_detect returns frames. Convert to time.
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
    subdivision = _normalize_subdivision(subdivision)
    if len(onset_times) == 0:
        return [0.0] * subdivision
    
    # 2. Grid Geometry
    ms_per_beat = 60000.0 / bpm
    steps_per_beat = subdivision / 4.0 # usually 4
    step_duration_ms = ms_per_beat / steps_per_beat
    step_duration_sec = step_duration_ms / 1000.0
    
    # Bar duration
    bar_duration_sec = (60.0 / bpm) * 4.0
    
    # 3. Accumulated Offsets
    # We want to find average offset for step indices 0, 1, ... 15.
    
    # Store lists of offsets for each step index
    step_offsets = {i: [] for i in range(subdivision)}
    
    for t in onset_times:
        # Map time to position in bar (modulo bar duration)
        # Assuming loop starts at 0.
        bar_pos = t % bar_duration_sec
        
        # Determine nearest grid step
        exact_step = bar_pos / step_duration_sec
        nearest_step_idx = int(round(exact_step)) % subdivision
        
        grid_time = nearest_step_idx * step_duration_sec
        
        # Deviation
        # Need to handle wrap-around for near 0? (e.g. 3.99s vs 0.0s)
        # Determine delta. 
        # If t is 3.99 and grid is 0.0, delta is -0.01 (early).
        # If t is 0.01 and grid is 0.0, delta is +0.01 (late).
        
        # Simple diff
        diff = bar_pos - grid_time
        
        # Wrap correction: if diff > half_step, means it belongs to previous or next?
        # Actually nearest_step logic handles most. But wrap around bar end:
        # If bar is 4.0s. t=3.99. Nearest step 0 (time 0.0).
        # diff = 3.99 - 0.0 = 3.99. HUGE.
        # Should be -0.01.
        
        if diff > (bar_duration_sec / 2):
            diff -= bar_duration_sec
        elif diff < -(bar_duration_sec / 2):
            diff += bar_duration_sec
            
        step_offsets[nearest_step_idx].append(diff * 1000.0) # convert to ms
        
    # 4. Average & Interpolate Missing
    raw_avgs = []
    for i in range(subdivision):
        vals = step_offsets[i]
        raw_avgs.append(float(np.mean(vals)) if vals else None)

    return _fill_missing_offsets(raw_avgs)
