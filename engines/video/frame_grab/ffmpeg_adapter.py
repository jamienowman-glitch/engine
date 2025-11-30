"""Helpers for ffmpeg-based frame extraction (placeholder)."""
from __future__ import annotations
from pathlib import Path
from typing import List


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_frame_pattern(output_dir: Path, stem: str = "frame") -> str:
    ensure_dir(output_dir)
    return str(output_dir / f"{stem}_%06d.png")
