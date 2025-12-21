from __future__ import annotations

from typing import List, Protocol
from dataclasses import dataclass
import numpy as np

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

from engines.audio_loops.models import LoopDetectRequest

@dataclass
class LoopCandidate:
    start_ms: float
    end_ms: float
    bpm: float
    loop_bars: int
    confidence: float

class AudioLoopsBackend(Protocol):
    def detect(self, file_path: str, req: LoopDetectRequest) -> List[LoopCandidate]:
        ...

class StubLoopsBackend(AudioLoopsBackend):
    def detect(self, file_path: str, req: LoopDetectRequest) -> List[LoopCandidate]:
        # Copied from previous service logic - TEST ONLY
        loops = []
        duration_ms = 10000.0 # Default
        bpm = 120.0
        beat_ms = 60000 / bpm
        
        for bars in req.target_bars:
            loop_dur = bars * 4 * beat_ms
            if loop_dur < duration_ms:
                start = 1000.0
                end = start + loop_dur
                
                loops.append(LoopCandidate(
                    start_ms=start,
                    end_ms=end,
                    bpm=bpm,
                    loop_bars=bars,
                    confidence=0.85
                ))
        return loops

class LibrosaLoopsBackend(AudioLoopsBackend):
    def detect(self, file_path: str, req: LoopDetectRequest) -> List[LoopCandidate]:
        if not HAS_LIBROSA:
            raise RuntimeError("Librosa not installed, cannot run LibrosaLoopsBackend")
            
        try:
            y, sr = librosa.load(file_path, sr=None)
        except Exception as e:
            raise ValueError(f"Failed to load audio: {e}")
        
        # 1. Beat Track
        try:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        except Exception:
             return []

        # tempo might be an array if dynamic? Usually scalar for standard call
        if isinstance(tempo, np.ndarray):
             tempo = tempo[0]
        
        if tempo <= 0:
            return []
            
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        if len(beat_times) < 4:
            return []
            
        # 2. Find Candidate Regions
        candidates = []
        sec_per_beat = 60.0 / tempo
        total_duration = librosa.get_duration(y=y, sr=sr)
        
        for bars in req.target_bars:
            beats_needed = bars * 4
            
            # Scan with stride of 4 beats (1 bar)
            for i in range(0, len(beat_times), 4):
                if i + beats_needed >= len(beat_times):
                    break
                
                start_t = beat_times[i]
                
                if i + beats_needed < len(beat_times):
                    end_t = beat_times[i + beats_needed]
                else:
                    end_t = start_t + (beats_needed * sec_per_beat)
                
                if end_t > total_duration:
                    continue
                    
                start_sample = librosa.time_to_samples(start_t, sr=sr)
                end_sample = librosa.time_to_samples(end_t, sr=sr)
                if end_sample > len(y): end_sample = len(y)
                
                segment = y[start_sample:end_sample]
                if len(segment) == 0: continue

                rms = float(np.sqrt(np.mean(segment**2)))
                
                if rms < 0.01:
                    continue
                    
                conf = min(1.0, rms * 10) # Crude boosting
                
                candidates.append(LoopCandidate(
                    start_ms=start_t * 1000.0,
                    end_ms=end_t * 1000.0,
                    bpm=float(tempo),
                    loop_bars=bars,
                    confidence=conf
                ))
        
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates[:10]
