from typing import List, Tuple
import numpy as np

def detect_onsets(audio_path: str) -> Tuple[List[float], List[float]]:
    """
    Returns (times_ms, amplitudes).
    """
    import librosa
    
    try:
        y, sr = librosa.load(audio_path, sr=None)
        if len(y) == 0:
            return [], []
            
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        # Get amplitudes at onsets (simple velocity proxy)
        # RMS energy? Or just peak in window?
        # Let's use simple RMS near onset.
        amplitudes = []
        hop_length = 512 # Default librosa hop
        for frame in onset_frames:
            start_sample = max(0, frame * hop_length)
            end_sample = min(len(y), (frame + 1) * hop_length)
            segment = y[start_sample:end_sample]
            amp = np.sqrt(np.mean(segment**2)) if len(segment) > 0 else 0.0
            amplitudes.append(float(amp))
            
        return [t * 1000.0 for t in onset_times], amplitudes
        
    except Exception:
        return [], []
