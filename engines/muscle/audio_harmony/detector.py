from __future__ import annotations
import numpy as np
from typing import Tuple
from engines.audio_harmony.models import KeyEstimate

# Standard profiles
# C Major: C D E F G A B (0, 2, 4, 5, 7, 9, 11 active)
# C Minor: C D Eb F G Ab Bb (0, 2, 3, 5, 7, 8, 10 active)
# We can use weights like Krumhansl-Schmuckler, but binary is often robust for simple loops.

MAJOR_PROFILE = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
MINOR_PROFILE = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def estimate_key(audio_path: str) -> KeyEstimate:
    import librosa
    
    try:
        y, sr = librosa.load(audio_path, sr=None)
        if len(y) == 0:
             return KeyEstimate(root="C", scale="unknown", confidence=0.0)
             
        # Harmonic content only
        y_harmonic, _ = librosa.effects.hpss(y)
        
        # Chroma CQT
        chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
        # Sum over time -> (12,) vector
        chroma_sum = np.sum(chroma, axis=1)
        # Normalize
        norm = np.linalg.norm(chroma_sum)
        if norm > 0:
            chroma_sum = chroma_sum / norm
            
        best_corr = -1.0
        best_root = 0
        best_scale = "major"
        
        # Correlate with all 12 shifts
        for i in range(12):
            # Roll input to align with profile (checking if input matches profile at root i)
            # Actually, we roll the profile to match root i
            
            # Major
            prof_maj = np.roll(MAJOR_PROFILE, i)
            corr_maj = np.corrcoef(chroma_sum, prof_maj)[0, 1]
            if corr_maj > best_corr:
                best_corr = corr_maj
                best_root = i
                best_scale = "major"
                
            # Minor
            prof_min = np.roll(MINOR_PROFILE, i)
            corr_min = np.corrcoef(chroma_sum, prof_min)[0, 1]
            if corr_min > best_corr:
                best_corr = corr_min
                best_root = i
                best_scale = "minor"
                
        return KeyEstimate(root=NOTES[best_root], scale=best_scale, confidence=float(best_corr))
        
    except Exception as e:
        # Fallback
        return KeyEstimate(root="C", scale="unknown", confidence=0.0)
