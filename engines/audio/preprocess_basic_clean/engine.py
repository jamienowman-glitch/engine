"""Atomic engine: AUDIO.PREPROCESS.BASIC_CLEAN_V1."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

from engines.audio.preprocess_basic_clean.types import PreprocessBasicCleanInput, PreprocessBasicCleanOutput


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _clean_path(src: Path, dst: Path) -> None:
    """Apply a lightweight ffmpeg filter chain for loudness/HPF/LPF."""
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
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=80,lowpass=f=15000",
        str(dst),
    ]
    subprocess.check_call(cmd)


def run(config: PreprocessBasicCleanInput) -> PreprocessBasicCleanOutput:
    """Perform basic audio cleanup (loudnorm + HPF/LPF) and return cleaned paths."""
    if not _ffmpeg_available():
        raise RuntimeError("ffmpeg is required for preprocessing")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    cleaned: List[Path] = []
    for src in config.input_paths:
        dest = config.output_dir / f"{src.stem}_clean.wav"
        _clean_path(src, dest)
        cleaned.append(dest)
    return PreprocessBasicCleanOutput(cleaned_paths=cleaned)
