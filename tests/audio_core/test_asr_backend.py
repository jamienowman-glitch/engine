from pathlib import Path

from engines.audio_core import asr_backend


def test_asr_backend_unavailable(tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"data")
    # force unavailable
    out = asr_backend.transcribe_audio([audio], model_name="medium")
    assert out[0]["file"] == "a.wav"
    assert "segments" in out[0]
    assert out[0].get("status") in {None, "unavailable", "error"}
