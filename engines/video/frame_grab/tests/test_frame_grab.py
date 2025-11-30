from pathlib import Path
from engines.video.frame_grab.engine import run, FrameGrabRequest


def test_frame_grab_placeholder(tmp_path: Path) -> None:
    resp = run(FrameGrabRequest(video_uri="video.mp4", mode="auto", frame_every_n_seconds=1.0, output_dir=tmp_path))
    assert resp.frames == []
