from pathlib import Path

import pytest

from engines.audio.segment_ffmpeg import engine
from engines.audio.segment_ffmpeg.types import SegmentFFmpegInput


class DummyRun:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, cmd, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(cmd)
        return type("R", (), {"stdout": "10.0", "stderr": ""})


def test_segment_ffmpeg_segments_metadata(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    input_path.write_bytes(b"fake")  # exists check
    out_dir = tmp_path / "out"

    # Stub ffmpeg + ffprobe
    dummy = DummyRun()
    monkeypatch.setattr(engine, "subprocess", type("S", (), {"check_call": lambda *a, **k: None, "run": dummy}))
    monkeypatch.setattr(engine.shutil, "which", lambda name: "ffmpeg")

    # Create fake segmented files after segmentation call
    def fake_segment(src_mp3: Path, dst_dir: Path, segment_seconds: int, overlap_seconds: int):
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "input_000.mp3").write_bytes(b"a")
        (dst_dir / "input_001.mp3").write_bytes(b"a")
        return sorted(dst_dir.glob("input_*.mp3"))

    monkeypatch.setattr(engine, "_segment_mp3", fake_segment)
    monkeypatch.setattr(engine, "_convert_to_mp3", lambda src, dst: dst.write_bytes(b"a"))
    monkeypatch.setattr(engine, "_ffprobe_duration", lambda p: 12.0)

    cfg = SegmentFFmpegInput(input_path=input_path, output_dir=out_dir, segment_seconds=5)
    output = engine.run(cfg)
    assert len(output.segments) == 2
    assert output.segments[0].start_seconds == 0.0
    assert output.segments[0].end_seconds == 5.0
    assert output.segments[1].start_seconds == 5.0
    assert output.segments[1].end_seconds == 10.0


def test_segment_ffmpeg_requires_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    input_path.write_bytes(b"fake")
    monkeypatch.setattr(engine.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        engine.run(SegmentFFmpegInput(input_path=input_path, output_dir=tmp_path / "o"))
