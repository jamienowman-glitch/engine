import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Tuple

try:
    import librosa
    import numpy as np
    from scipy import signal
    HAS_DSP = True
except ImportError:
    HAS_DSP = False

logger = logging.getLogger(__name__)

class MultiCamAlignBackend(Protocol):
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str) -> float:
        """
        Calculates the offset (in milliseconds) to delay the angle audio 
        so it aligns with the master audio.
        Positive offset -> angle starts LATER than master (angle needs to be shifted right or master left?)
        
        If Master has feature at T=10s, and Angle has same feature at T=5s:
        Angle is early. Angle needs +5s delay.
        Offset = +5000.
        
        If Master has feature at T=5s, and Angle has same feature at T=10s:
        Angle is late. Angle needs -5s shift (or start at -5s).
        Offset = -5000.
        """
        ...

class StubAlignBackend(MultiCamAlignBackend):
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str) -> float:
        logger.info("StubAlignBackend: returning 0 offset")
        return 0.0

class LibrosaAlignBackend(MultiCamAlignBackend):
    def __init__(self, sr: int = 8000, max_duration: int = 300):
        self.sr = sr
        self.max_duration = max_duration

    def calculate_offset(self, master_audio_path: str, angle_audio_path: str) -> float:
        if not HAS_DSP:
            logger.warning("Librosa/Scipy not found, using stub behavior 0.0")
            return 0.0
            
        try:
            # Load audio using librosa (uses ffmpeg implicitly often or soundfile)
            # Limit duration to avoid massive RAM usage on full clips
            y_master, _ = librosa.load(master_audio_path, sr=self.sr, duration=self.max_duration, mono=True)
            y_angle, _ = librosa.load(angle_audio_path, sr=self.sr, duration=self.max_duration, mono=True)
            
            # Cross Correlate
            # Mode='full' to find full lag range
            correlation = signal.correlate(y_master, y_angle, mode='full', method='fft')
            lags = signal.correlation_lags(len(y_master), len(y_angle), mode='full')
            
            lag_idx = np.argmax(correlation)
            lag_samples = lags[lag_idx]
            
            # Lag in samples: if lag > 0, it means y_angle needs to shift "right" ?
            # Scipy correlate(a, b):
            # If peak is at lag k, then a[n] ~= b[n+k]
            # master[n] ~= angle[n + lag]
            # If lag is positive (e.g. +5 samples). master[0] ~= angle[5].
            # This means Angle is "ahead" (feature happens later in angle).
            # Wait. master[n] is at time T. angle[n+k] is at time T+k/sr.
            # So the feature in Angle is at T+Lag.
            # The feature in Master is at T.
            # So Angle is LATER than Master by Lag.
            # To align Angle to Master, we must move Angle "Left" by Lag (negative shift).
            # My Protocol definition: "Positive offset -> delay angle".
            # If Angle is late (feature at 10s vs 5s), we need to start it earlier (-5s).
            # So Offset should be negative of the Lag time??
            
            # Let's verify with standard convention.
            # If lag is positive, Angle is delayed relative to Master. 
            # We want offset to *correct* it? Or describe the state?
            # Protocol: "Positive offset -> angle starts LATER than master".
            # This describes the *state* of the clip.
            # If offset is +5000ms, it means Angle track starts at T=5000.
            # Wait. If Angle track starts at 5000, its feature at index 0 (if raw) is at 5000.
            # If Master feature is at 5000 (index K) and Angle feature is at 0 (index 0).
            # Then Master is late.
            
            # Let's stick to simple "Shift required applied to Angle".
            # If Lag is +5 samples. master[0] ~= angle[5].
            # Feature is at 0 in Master, 5 in Angle.
            # Angle is "late" by 5 samples.
            # To sync, we must START the Angle clip at -5 samples (or -time).
            # So Offset = - (Lag / sr).
            
            offset_seconds = - (lag_samples / self.sr)
            offset_ms = offset_seconds * 1000.0
            
            logger.info(f"Calculated offset: {offset_ms:.2f}ms (lag: {lag_samples} samples)")
            return float(offset_ms)
            
        except Exception as e:
            logger.error(f"Error calculating offset: {e}")
            return 0.0

