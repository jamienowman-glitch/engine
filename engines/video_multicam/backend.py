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
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str, max_duration: int = 300) -> Tuple[float, float]:
        """
        Calculates the offset (in milliseconds) and confidence score (0.0-1.0).
        Positive offset -> Angle starts LATER than Master.
        """
        ...

class StubAlignBackend(MultiCamAlignBackend):
    def calculate_offset(self, master_audio_path: str, angle_audio_path: str, max_duration: int = 300) -> Tuple[float, float]:
        logger.info("StubAlignBackend: returning 0 offset")
        return 0.0, 1.0

class LibrosaAlignBackend(MultiCamAlignBackend):
    def __init__(self, sr: int = 8000, max_duration: int = 300):
        self.sr = sr
        self.default_max_duration = max_duration

    def calculate_offset(self, master_audio_path: str, angle_audio_path: str, max_duration: Optional[int] = None) -> Tuple[float, float]:
        if not HAS_DSP:
            logger.warning("Librosa/Scipy not found, using stub behavior 0.0")
            return 0.0, 0.0
            
        duration = max_duration if max_duration is not None else self.default_max_duration

        try:
            # Load audio using librosa
            y_master, _ = librosa.load(master_audio_path, sr=self.sr, duration=duration, mono=True)
            y_angle, _ = librosa.load(angle_audio_path, sr=self.sr, duration=duration, mono=True)
            
            # Cross Correlate
            n_master = len(y_master)
            n_angle = len(y_angle)
            
            if n_master == 0 or n_angle == 0:
                 return 0.0, 0.0

            # Normalize for confidence scoring
            # Regular cross-correlation amplitude depends on signal energy.
            # Using coefficient normalization? Or just rely on peak prominence?
            # Standard way: Pearson correlation coefficient at lag.
            # Scipy correlate doesn't normalize by default.
            
            # Use FFT based correlation
            correlation = signal.correlate(y_master, y_angle, mode='full', method='fft')
            lags = signal.correlation_lags(n_master, n_angle, mode='full')
            
            lag_idx = np.argmax(correlation)
            lag_samples = lags[lag_idx]
            peak_val = correlation[lag_idx]
            
            # Calculate normalization factor for confidence (approximate Pearson)
            # Conf = CrossCorr / (Norm(Master) * Norm(Angle))
            # But overlapping windows differ.
            # For simplicity in V1: 
            # We can use the peak value divided by geometric mean of energies?
            # Or just return raw normalized cross-correlation if we centered data?
            # Let's do simple energy normalization.
            
            energy_m = np.sqrt(np.dot(y_master, y_master))
            energy_a = np.sqrt(np.dot(y_angle, y_angle))
            
            confidence = 0.0
            if energy_m > 0 and energy_a > 0:
                confidence = peak_val / (energy_m * energy_a)
            
            # Clip confidence
            confidence = max(0.0, min(1.0, float(confidence)))

            # Offset calculation
            # Lag L means master[n] ~ angle[n+L]
            # If L > 0, angle is "early" in the array indices relative to master?
            # Wait. 
            # correlate(u, v)[k] = sum_n u[n] * conj(v[n+k]) NO.
            # scipy.signal.correlate(in1, in2)
            # If in1 is shifted version of in2 by delta: in1[x] = in2[x - delta]
            # lag index will correspond to ...
            # Let's trust previous logic analysis or standard test:
            # If lag is +samples. Master is "ahead" of Angle? No.
            # Previous analysis:
            # offset_seconds = - (lag_samples / self.sr)
            # This worked for "Positive offset -> Angle starts LATER".
            
            offset_seconds = - (lag_samples / self.sr)
            offset_ms = offset_seconds * 1000.0
            
            logger.info(f"Calculated offset: {offset_ms:.2f}ms (lag: {lag_samples}), confidence: {confidence:.2f}")
            return float(offset_ms), confidence
            
        except Exception as e:
            logger.error(f"Error calculating offset: {e}")
            return 0.0, 0.0

