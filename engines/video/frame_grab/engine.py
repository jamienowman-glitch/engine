"""Atomic engine: VIDEO.INGEST.FRAME_GRAB_V1."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from engines.video.frame_grab.types import FrameGrabInput, FrameGrabOutput, FrameGrabResult


def _ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for frame grab")


def _auto_frames(config: FrameGrabInput) -> List[FrameGrabResult]:
    max_frames = config.max_frames or 3
    interval = config.frame_every_n_seconds
    stem = Path(config.video_uri).stem or "frame"
    pattern = config.output_dir / f"{stem}_%03d.png"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        config.video_uri,
        "-vf",
        f"fps=1/{interval}",
        "-vframes",
        str(max_frames),
        str(pattern),
    ]
    subprocess.check_call(cmd)
    frames: List[FrameGrabResult] = []
    for idx, path in enumerate(sorted(config.output_dir.glob(f"{stem}_*.png"))):
        frames.append(FrameGrabResult(timestamp_ms=int(idx * interval * 1000), frame_path=path, meta={"mode": "auto"}))
    return frames


def _manual_frames(config: FrameGrabInput) -> List[FrameGrabResult]:
    frames: List[FrameGrabResult] = []
    stem = Path(config.video_uri).stem or "frame"
    for idx, ts in enumerate(config.timestamps_ms or []):
        out_path = config.output_dir / f"{stem}_{idx:03d}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{ts/1000:.3f}",
            "-i",
            config.video_uri,
            "-vframes",
            "1",
            str(out_path),
        ]
        subprocess.check_call(cmd)
        frames.append(FrameGrabResult(timestamp_ms=ts, frame_path=out_path, meta={"mode": "manual"}))
    return frames


def run(config: FrameGrabInput) -> FrameGrabOutput:
    _ensure_ffmpeg()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    if config.mode == "auto":
        frames = _auto_frames(config)
    else:
        frames = _manual_frames(config)
    video_meta: Dict[str, Any] = {"source": config.video_uri}
    return FrameGrabOutput(frames=frames, video_meta=video_meta)
