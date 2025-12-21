import subprocess
import os
from typing import Protocol

class VideoStabiliseBackend(Protocol):
    def detect_stability(self, input_path: str, output_trf: str) -> None:
        """
        Runs the 1st pass of synchronisation (vidstabdetect) to generate a transform file (.trf).
        """
        ...

class FfmpegStabiliseBackend:
    def detect_stability(self, input_path: str, output_trf: str) -> None:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_trf)), exist_ok=True)
        
        # Run vidstabdetect
        # stepsize=6, shakiness=8, accuracy=10 -> moderately aggressive, reasonable speed
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"vidstabdetect=stepsize=6:shakiness=8:accuracy=10:result={output_trf}",
            "-f", "null", "-"
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            encoded_stderr = e.stderr.decode('utf-8') if e.stderr else 'No stderr'
            raise RuntimeError(f"FFmpeg vidstabdetect failed: {encoded_stderr}")

class StubStabiliseBackend:
    def detect_stability(self, input_path: str, output_trf: str) -> None:
        # Create a dummy TRF file (content doesn't matter for stub, but real vidstabtransform needs real binary)
        # For testing, we might just write "stub_transform"
        with open(output_trf, "w") as f:
            f.write("stub_transform_data")
