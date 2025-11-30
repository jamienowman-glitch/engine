from engines.align.audio_text_bars.engine import run, AlignAudioTextBarsRequest


def test_audio_text_bars_placeholder() -> None:
    req = AlignAudioTextBarsRequest(asr_payloads=[], beat_metadata={})
    resp = run(req)
    assert resp.bars == []
