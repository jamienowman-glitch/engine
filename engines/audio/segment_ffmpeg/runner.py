"""CLI runner for AUDIO.SEGMENT.FFMPEG_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.audio.segment_ffmpeg.engine import run
from engines.audio.segment_ffmpeg.types import SegmentFFmpegInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Segment audio/video via ffmpeg")
    parser.add_argument("input_path", type=Path, help="Input audio/video path")
    parser.add_argument("output_dir", type=Path, help="Directory for segments")
    parser.add_argument("--segment-seconds", type=int, default=90, help="Segment length in seconds")
    parser.add_argument("--overlap-seconds", type=int, default=0, help="Overlap between segments")
    args = parser.parse_args()
    cfg = SegmentFFmpegInput(
        input_path=args.input_path,
        output_dir=args.output_dir,
        segment_seconds=args.segment_seconds,
        overlap_seconds=args.overlap_seconds,
    )
    resp = run(cfg)
    print(f"Created {len(resp.segments)} segment(s) -> {args.output_dir}")


if __name__ == "__main__":
    main()
