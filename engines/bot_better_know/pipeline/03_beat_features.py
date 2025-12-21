"""Compute tempo and rhythmic grids for each segment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import librosa


def process_file(path: Path, dst: Path) -> None:
    y, sr = librosa.load(path, sr=44100, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    downbeats = [float(b) for i, b in enumerate(beats) if i % 4 == 0]
    grid16 = 60.0 / (tempo * 4.0) if tempo else 0.0
    out = {"bpm": float(tempo), "downbeats": downbeats, "grid16": float(grid16)}
    out_path = dst / f"{path.name}.meta.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze BPM and beat grid")
    parser.add_argument("input_dir", help="Directory with segmented mp3 audio")
    parser.add_argument("output_dir", help="Directory to store meta JSON files")
    args = parser.parse_args()

    src = Path(args.input_dir)
    dst = Path(args.output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    for mp3 in sorted(src.glob("*.mp3")):
        process_file(mp3, dst)


if __name__ == "__main__":
    main()
