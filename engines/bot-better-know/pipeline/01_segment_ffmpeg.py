"""Extract mono mp3 audio and chunk into ~90 second segments."""
from __future__ import annotations

import argparse
import pathlib
import shlex
import subprocess


def sh(args: list[str]) -> None:
    print(">>", " ".join(shlex.quote(a) for a in args))
    subprocess.check_call(args)


def process_file(path: pathlib.Path, dst: pathlib.Path) -> None:
    base = path.stem
    tmp_mp3 = dst / f"{base}.mp3"
    sh(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "44100",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(tmp_mp3),
        ]
    )
    sh(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(tmp_mp3),
            "-f",
            "segment",
            "-segment_time",
            "90",
            "-c",
            "copy",
            str(dst / f"{base}_%03d.mp3"),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Segment freestyle uploads for Whisper ASR")
    parser.add_argument("input_dir", help="Directory with source audio/video")
    parser.add_argument("output_dir", help="Directory to place segmented mp3 files")
    args = parser.parse_args()

    src = pathlib.Path(args.input_dir)
    dst = pathlib.Path(args.output_dir)
    dst.mkdir(parents=True, exist_ok=True)

    for file_path in src.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".mp3", ".mp4", ".wav", ".m4a"}:
            process_file(file_path, dst)


if __name__ == "__main__":
    main()
