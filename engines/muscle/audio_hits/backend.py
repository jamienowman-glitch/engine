from __future__ import annotations

import os
from typing import List, Protocol
from dataclasses import dataclass
import tempfile
import shutil

# Try imports
try:
    import numpy as np
    import librosa
    import soundfile as sf
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    np = None

from engines.audio_hits.models import HitDetectRequest, HitEvent

@dataclass
class OnsetResult:
    start_ms: float
    end_ms: float
    peak_db: float

class AudioHitsBackend(Protocol):
    def detect(self, file_path: str, req: HitDetectRequest) -> List[OnsetResult]:
        ...

class StubHitsBackend(AudioHitsBackend):
    def detect(self, file_path: str, req: HitDetectRequest) -> List[OnsetResult]:
        # Strictly for tests where "real_muscle" is explicitly disabled
        events: List[OnsetResult] = []
        hit_count = 5
        duration = 5000
        interval = duration / hit_count

        # Respect the min_interval_ms parameter similar to Librosa backend (compare in ms)
        min_interval_ms = req.min_interval_ms
        last_time = -10000.0  # ms

        for i in range(hit_count):
            t = i * interval + 100  # t is in ms
            # Skip if this onset is too close to the last one
            if t - last_time < min_interval_ms:
                continue

            start = max(0, t - req.pre_roll_ms)
            end = t + req.post_roll_ms
            events.append(OnsetResult(
                start_ms=float(start),
                end_ms=float(end),
                peak_db=-6.0 - i
            ))
            last_time = t
        return events

class LibrosaHitsBackend(AudioHitsBackend):
    def detect(self, file_path: str, req: HitDetectRequest) -> List[OnsetResult]:
        if not HAS_LIBROSA:
            raise RuntimeError("Librosa/numpy/soundfile not installed, cannot run LibrosaHitsBackend")
            
        # 1. Load Audio
        # Load as mono, default sr=22050 is usually fine for onset
        try:
            y, sr = librosa.load(file_path, sr=None, mono=True)
        except Exception as e:
            raise ValueError(f"Failed to load audio: {e}")

        # 2. Onset Detection
        # simple onset detect
        # We can tune backtracking to find the true start
        try:
            onsets_frames = librosa.onset.onset_detect(
                y=y, sr=sr, 
                backtrack=True,
                units='frames'
            )
            onsets_times = librosa.frames_to_time(onsets_frames, sr=sr)
        except Exception as e:
            # Fallback for very short files or silence
            return []

        # 3. Filter and Build Results
        results = []
        min_interval_sec = req.min_interval_ms / 1000.0
        
        last_time = -100.0
        
        for t in onsets_times:
            if t - last_time < min_interval_sec:
               continue
               
            # Basic window for peak check
            # Look ahead a bit
            frame_idx = librosa.time_to_frames(t, sr=sr)
            # Check peak in next 100ms
            check_frames = librosa.time_to_frames(0.1, sr=sr)
            
            # Bounds check
            if frame_idx >= len(y): continue
            
            segment = y[frame_idx : min(len(y), frame_idx + check_frames)]
            if len(segment) == 0: continue
            
            peak_amp = np.max(np.abs(segment))
            peak_db = librosa.amplitude_to_db([peak_amp], top_db=80)[0]
            
            if peak_db < req.min_peak_db:
                continue
                
            # Construct Hit
            # Convert to ms
            t_ms = t * 1000.0
            start_ms = max(0, t_ms - req.pre_roll_ms)
            end_ms = t_ms + req.post_roll_ms
            
            # Ensure we don't go past end
            file_dur_ms = (len(y) / sr) * 1000
            end_ms = min(end_ms, file_dur_ms)
            
            results.append(OnsetResult(
                start_ms=start_ms,
                end_ms=end_ms,
                peak_db=float(peak_db)
            ))
            last_time = t
            
        return results
