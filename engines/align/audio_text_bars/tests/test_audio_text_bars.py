import pytest

from engines.align.audio_text_bars.engine import run
from engines.align.audio_text_bars.types import AlignAudioTextBarsInput


def test_align_audio_text_bars_creates_bars() -> None:
    payloads = [{"segments": [{"text": "Hello World"}, {"text": "Line two"}]}]
    out = run(AlignAudioTextBarsInput(asr_payloads=payloads, beat_metadata={}))
    assert len(out.bars) == 2
    assert out.bars[0].bar_index == 1
    assert out.bars[0].text_norm == "hello world"


def test_align_requires_payloads() -> None:
    with pytest.raises(ValueError):
        AlignAudioTextBarsInput(asr_payloads=[], beat_metadata={})
