import pytest
from pathlib import Path

from engines.video import frame_grab as mod
from engines.video.frame_grab.engine import run
from engines.video.frame_grab.types import FrameGrabInput


def test_frame_grab_auto_invokes_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_call(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        # simulate ffmpeg output frame
        (tmp_path / "video_000.png").write_bytes(b"frame")

    monkeypatch.setattr(mod, "subprocess", type("S", (), {"check_call": fake_call}))
    monkeypatch.setattr(mod.shutil, "which", lambda name: "ffmpeg")

    out = run(FrameGrabInput(video_uri="video.mp4", mode="auto", frame_every_n_seconds=1.0, output_dir=tmp_path))
    assert calls, "ffmpeg should be called"
    assert len(out.frames) == 1
    assert out.frames[0].timestamp_ms == 0


def test_frame_grab_manual_invokes_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_call(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(cmd)
        # create file per call
        out_path = Path(cmd[-1])
        out_path.write_bytes(b"frame")

    monkeypatch.setattr(mod, "subprocess", type("S", (), {"check_call": fake_call}))
    monkeypatch.setattr(mod.shutil, "which", lambda name: "ffmpeg")

    out = run(FrameGrabInput(video_uri="video.mp4", mode="manual", timestamps_ms=[100, 200], output_dir=tmp_path))
    assert len(out.frames) == 2
    assert out.frames[0].timestamp_ms == 100
    assert calls, "ffmpeg should be called"


def test_frame_grab_requires_ffmpeg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        run(FrameGrabInput(video_uri="video.mp4", mode="auto", frame_every_n_seconds=1.0, output_dir=tmp_path))
