from engines.audio.asr_whisper.engine import run, ASRWhisperRequest


def test_asr_whisper_placeholder() -> None:
    req = ASRWhisperRequest(audio_paths=[])
    resp = run(req)
    assert resp.results == []
