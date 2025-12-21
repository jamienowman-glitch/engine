from engines.audio_shared.health import is_tool_available
from typing import Dict
import subprocess
import os

def run_demucs_separation(input_path: str, output_dir: str, model_name: str = "htdemucs") -> Dict[str, str]:
    """
    Runs demucs on input_path, outputs to output_dir.
    Returns map of role -> file_path.
    """
    if not is_tool_available("demucs"):
        raise RuntimeError("Demucs executable not found in path. Please install 'demucs'.")

    # Cmd: demucs -n <model> -o <out_dir> <input>
    cmd = [
        "demucs",
        "-n", model_name,
        "-o", output_dir,
        input_path
    ]
    
    try:
        # Timeout after 5 minutes (300s) to prevent hangs
        # Capture stderr for debugging
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=300)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Demucs separation timed out after 300 seconds.")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown error"
        raise RuntimeError(f"Demucs failed: {error_msg}")
        
    # Resolve outputs
    # Demucs creates subfolder <model_name>/<track_name>/
    file_stem = Path(input_path).stem
    track_dir = Path(output_dir) / model_name / file_stem
    
    if not track_dir.exists():
         raise RuntimeError(f"Demucs did not create expected directory: {track_dir}")
         
    results = {}
    for role in ["drums", "bass", "vocals", "other"]:
        f_path = track_dir / f"{role}.wav"
        if f_path.exists():
            results[role] = str(f_path)
            
    return results
