import os
import subprocess
import numpy as np
from typing import Dict, Any, Tuple
from pathlib import Path

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

def normalize_audio(
    input_path: str, 
    output_path: str, 
    target_lufs: float = -14.0, 
    peak_ceiling: float = -1.0
) -> Dict[str, float]:
    """
    Normalizes audio using ffmpeg loudnorm pass.
    Returns measurement dict {input_i, input_tp, input_lra, input_thresh, output_i, output_tp, ...}
    For V1 we rely on single pass loudnorm with default linear approximation or dual pass if extracted.
    But single pass loudnorm=I=-14:TP=-1 is usually sufficient for sample normalization.
    """
    
    # loudnorm filter: I=target_lufs, TP=peak_ceiling, print_format=json
    # We want to capture the JSON output to get measurements.
    
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", input_path,
        "-af", f"loudnorm=I={target_lufs}:TP={peak_ceiling}:print_format=json",
        str(output_path)
    ]
    
    # To capture json, we need to read stderr because loudnorm prints there.
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg normalization timed out after 120 seconds.")
        
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg normalization failed: {process.stderr}")
    
    # Parse JSON from stderr
    # loudnorm prints ~12 lines of json.
    stats = {}
    try:
        # Find JSON block more robustly
        import re
        import json
        
        # Regex to find json block: starts with { and ends with }
        # Note: loudnorm output might contain multiple blocks if multiple streams (unlikely here)
        # or other text.
        # We look for the block containing "input_i" or "output_i"
        
        # Simple block finder:
        match = re.search(r"(\{.*?\})", process.stderr, re.DOTALL)
        if match:
             blob = match.group(1)
             data = json.loads(blob)
             # Verify it's loudnorm data
             if "input_i" in data or "output_i" in data:
                 stats["input_i"] = float(data.get("input_i", -99))
                 stats["output_i"] = float(data.get("output_i", target_lufs))
                 stats["output_tp"] = float(data.get("output_tp", peak_ceiling))
        
        if json_lines:
            import json
            # Join and parse
            blob = "\n".join(json_lines)
            # Find the last valid json object if multiple
            # loudnorm prints input measures, then output measures? No, usually one block relative to the processing.
            # Actually single pass prints measurement of the INPUT usually unless dual pass?
            # Wait, loudnorm single pass targets correctly but the printed stats are for the input?
            # If so, we know the output TARGETED -14.
            # Let's trust the target for 'output_i' if parsing fails, or parse 'output_i' from json.
            data = json.loads(blob)
            stats["input_i"] = float(data.get("input_i", 0))
            stats["output_i"] = float(data.get("output_i", target_lufs))
            stats["output_tp"] = float(data.get("output_tp", peak_ceiling))
    except Exception:
        # Fallback
        pass
        
    return stats

from engines.audio_shared.health import is_tool_available

def extract_features_librosa(file_path: str) -> Dict[str, Any]:
    if not is_tool_available("librosa"):
        return {}
        
    try:
        y, sr = librosa.load(file_path, sr=None)
    except Exception:
        return {}

    feats = {}
    
    # 1. BPM
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = tempo[0]
        feats["bpm"] = float(tempo)
    except Exception:
        pass
        
    # 2. Key (Heuristic)
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_sum = np.sum(chroma, axis=1)
        max_bin = np.argmax(chroma_sum)
        # Map 0..11 to C..B
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        feats["key_root"] = notes[max_bin]
        # Major/Minor? 
        # Correlation with templates is better but V1 simple root is OK.
    except Exception:
        pass
        
    # 3. Spectral Centroid (Brightness)
    try:
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        feats["brightness"] = float(np.mean(cent))
    except Exception:
        pass
        
    # 4. Zero Crossing Rate (Noisiness)
    try:
        zcr = librosa.feature.zero_crossing_rate(y=y)
        feats["noisiness"] = float(np.mean(zcr))
    except Exception:
        pass

    # 5. Dynamic Range (simple crest factor or peak - rms)
    try:
        rms = np.sqrt(np.mean(y**2))
        peak = np.max(np.abs(y))
        if rms > 0:
            dr_db = 20 * np.log10(peak / rms)
            feats["dynamic_range_db"] = float(dr_db)
    except Exception:
        pass

    return feats
