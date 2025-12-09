from pathlib import Path

import pytest

from engines.audio.asr_whisper.engine import run
from engines.audio.asr_whisper.types import ASRWhisperInput, ASRWhisperOutput


def test_asr_whisper_stub(tmp_path: Path) -> None:
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"data")
    out = run(ASRWhisperInput(audio_paths=[audio]))
    assert isinstance(out, ASRWhisperOutput)
    assert len(out.results) == 1
    assert out.results[0].file == "a.mp3"


def test_asr_whisper_requires_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ASRWhisperInput(audio_paths=[])
