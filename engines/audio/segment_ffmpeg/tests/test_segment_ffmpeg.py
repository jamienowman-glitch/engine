from pathlib import Path
from engines.audio.segment_ffmpeg.engine import run, SegmentFFmpegRequest


def test_segment_ffmpeg_placeholder(tmp_path: Path) -> None:
    req = SegmentFFmpegRequest(input_path=tmp_path / "in.mp3", output_dir=tmp_path / "out")
    resp = run(req)
    assert resp.segments == []
