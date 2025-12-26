from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from engines.video_render.models import RenderPlan


class FFmpegError(RuntimeError):
    def __init__(self, message: str, *, stage: str = "ffmpeg", stderr_tail: str | None = None, hint: str | None = None):
        super().__init__(message)
        self.stage = stage
        self.stderr_tail = stderr_tail
        self.hint = hint

    def __str__(self) -> str:
        base = f"[{self.stage}] {super().__str__()}"
        if self.hint:
            base += f" (hint: {self.hint})"
        return base



_HW_ENCODERS_CACHE: Optional[set[str]] = None


def get_available_hardware_encoders() -> set[str]:
    """Detect available hardware encoders via ffmpeg -encoders."""
    global _HW_ENCODERS_CACHE
    if _HW_ENCODERS_CACHE is not None:
        return _HW_ENCODERS_CACHE

    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5)
        encoders = set()
        for line in res.stdout.splitlines():
            if "h264_videotoolbox" in line:
                encoders.add("h264_videotoolbox")
            if "h264_nvenc" in line:
                encoders.add("h264_nvenc")
            if "hevc_videotoolbox" in line:
                encoders.add("hevc_videotoolbox")
            if "hevc_nvenc" in line:
                encoders.add("hevc_nvenc")
        _HW_ENCODERS_CACHE = encoders
        return encoders
    except Exception:
        _HW_ENCODERS_CACHE = set()
        return set()


def run_ffmpeg(plan: RenderPlan, timeout: int = 120, *, stage: str = "ffmpeg", hint: str | None = None) -> str:
    """Execute the first step of a render plan via ffmpeg.

    Returns the output path. Raises FFmpegError on failure.
    """
    if not plan.steps:
        raise FFmpegError("render plan has no steps", stage=stage, hint=hint)
    step = plan.steps[0]
    if not step.ffmpeg_args:
        raise FFmpegError("ffmpeg args missing", stage=stage, hint=hint)
    # Ensure output directory exists
    out_path = Path(plan.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Capture stderr for better error reporting
        subprocess.run(step.ffmpeg_args, check=True, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"ffmpeg timed out: {exc}", stage=stage, hint=hint) from exc
    except subprocess.CalledProcessError as exc:
        # Extract last few lines of stderr
        err_log = exc.stderr or ""
        tail = "\n".join(err_log.splitlines()[-10:])
        raise FFmpegError(f"ffmpeg failed (code {exc.returncode}):\n{tail}", stage=stage, stderr_tail=tail, hint=hint) from exc
    except Exception as exc:
        raise FFmpegError(f"ffmpeg failed: {exc}", stage=stage, hint=hint) from exc
    return str(out_path)
