"""Atomic engine: AUDIO.SEGMENT.FFMPEG_V1."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

from engines.audio.segment_ffmpeg.types import (
    SegmentFFmpegInput,
    SegmentFFmpegOutput,
    SegmentMetadata,
)


def _ffprobe_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _convert_to_mp3(src: Path, dst_mp3: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        "-acodec",
        "libmp3lame",
        "-q:a",
        "2",
        str(dst_mp3),
    ]
    subprocess.check_call(cmd)


def _segment_mp3(src_mp3: Path, dst_dir: Path, segment_seconds: int, overlap_seconds: int) -> List[Path]:
    pattern = dst_dir / f"{src_mp3.stem}_%03d.mp3"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src_mp3),
        "-f",
        "segment",
        "-segment_time",
        str(segment_seconds),
        "-c",
        "copy",
        str(pattern),
    ]
    if overlap_seconds > 0:
        cmd.extend(["-segment_time_delta", str(overlap_seconds)])
    subprocess.check_call(cmd)
    return sorted(dst_dir.glob(f"{src_mp3.stem}_*.mp3"))


def run(config: SegmentFFmpegInput) -> SegmentFFmpegOutput:
    """Segment audio/video into fixed-length mp3 chunks using ffmpeg."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to mono mp3 first to keep segmentation simple.
    tmp_mp3 = config.output_dir / f"{config.input_path.stem}.mp3"
    _convert_to_mp3(config.input_path, tmp_mp3)

    # Segment
    segment_paths = _segment_mp3(tmp_mp3, config.output_dir, config.segment_seconds, config.overlap_seconds)
    duration = _ffprobe_duration(tmp_mp3)

    segments: List[SegmentMetadata] = []
    for idx, path in enumerate(segment_paths):
        start = idx * config.segment_seconds
        end = min(duration, (idx + 1) * config.segment_seconds)
        segments.append(SegmentMetadata(path=path, start_seconds=float(start), end_seconds=float(end)))
    return SegmentFFmpegOutput(segments=segments)
