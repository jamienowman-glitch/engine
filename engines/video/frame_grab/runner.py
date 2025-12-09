"""CLI runner for VIDEO.INGEST.FRAME_GRAB_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.video.frame_grab.engine import run
from engines.video.frame_grab.types import FrameGrabInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Grab frames from video")
    parser.add_argument("video_uri", help="Video file/URI")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto")
    parser.add_argument("--frame-every", type=float, default=None, help="Seconds between frames (auto mode)")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames (auto mode)")
    parser.add_argument("--timestamps-ms", nargs="*", type=int, default=None, help="Timestamps in ms (manual mode)")
    args = parser.parse_args()
    cfg = FrameGrabInput(
        video_uri=args.video_uri,
        mode=args.mode, 
        frame_every_n_seconds=args.frame_every,
        max_frames=args.max_frames,
        timestamps_ms=args.timestamps_ms,
        output_dir=args.output_dir,
    )
    res = run(cfg)
    print(f"Frames: {len(res.frames)} -> {args.output_dir}")


if __name__ == "__main__":
    main()
