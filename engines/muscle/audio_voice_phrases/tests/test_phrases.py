import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from engines.audio_voice_phrases.service import AudioVoicePhrasesService
from engines.audio_voice_phrases.models import VoicePhraseDetectRequest
from engines.audio_shared.health import DependencyInfo
from engines.media_v2.models import MediaAsset, DerivedArtifact

def _create_temp_transcript():
    data = [
        {"word": "Welcome", "start_ms": 1000, "end_ms": 1500, "conf": 0.9},
        {"word": "to", "start_ms": 1500, "end_ms": 1800, "conf": 0.9},
        {"word": "the", "start_ms": 1800, "end_ms": 2000, "conf": 0.9},
        {"word": "jungle.", "start_ms": 2000, "end_ms": 2500, "conf": 0.9},
        # Gap 1500ms (2500 -> 4000)
        {"word": "We", "start_ms": 4000, "end_ms": 4200, "conf": 0.8},
        {"word": "got", "start_ms": 4200, "end_ms": 4500, "conf": 0.8},
        {"word": "fun", "start_ms": 4500, "end_ms": 4900, "conf": 0.8}
    ]
    f = tempfile.NamedTemporaryFile(mode='w', delete=False)
    json.dump(data, f)
    f.close()
    return f.name


def _fake_dependencies(librosa_available: bool) -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(True, "6.0", None),
        "ffprobe": DependencyInfo(True, "6.0", None),
        "demucs": DependencyInfo(True, "4.1", None),
        "librosa": DependencyInfo(librosa_available, "0.10.0" if librosa_available else None, None if librosa_available else "missing"),
    }

def test_detect_phrases_stub():
    transcript_path = _create_temp_transcript()
    
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav"
    )
    
    # Mock list_artifacts_for_asset to return the transcript
    mock_media.list_artifacts_for_asset.return_value = [
        DerivedArtifact(
            id="trans_1", parent_asset_id="asset_1", tenant_id="t1", env="dev", 
            kind="asr_transcript", uri=transcript_path,
            start_ms=0, end_ms=5000
        )
    ]
    
    def fake_reg(req):
        return DerivedArtifact(
            id=f"phrase_{req.start_ms}", 
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id, env=req.env,
            kind=req.kind, uri=req.uri,
            start_ms=req.start_ms, end_ms=req.end_ms,
            meta=req.meta
        )
    mock_media.register_artifact.side_effect = fake_reg
    
    service = AudioVoicePhrasesService(media_service=mock_media)
    
    try:
        req = VoicePhraseDetectRequest(
            tenant_id="t1", env="dev", asset_id="asset_1",
            max_gap_ms=500
        )
        
        with patch("engines.audio_voice_phrases.service.check_dependencies") as mock_check:
            mock_check.return_value = _fake_dependencies(True)
            res = service.detect_phrases(req)
        assert res.meta["backend_info"]["backend_type"] == "librosa"
        
        # Expect 2 phrases from stub data
        # 1. "Welcome to the jungle." (1000-2500)
        # 2. "We got fun" (4000-4900)
        
        assert len(res.phrases) == 2
        assert len(res.artifact_ids) == 2
        
        p1 = res.phrases[0]
        assert p1.transcript == "Welcome to the jungle."
        assert p1.start_ms == 1000
        assert p1.end_ms == 2500
        
        p2 = res.phrases[1]
        assert "We got fun" in p2.transcript
        assert p2.start_ms == 4000
    finally:
        if os.path.exists(transcript_path):
            os.unlink(transcript_path)

def test_detect_phrases_merge_all():
    transcript_path = _create_temp_transcript()

    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a", tenant_id="t", env="d", kind="audio", source_uri="u")
    
    mock_media.list_artifacts_for_asset.return_value = [
        DerivedArtifact(
            id="trans_1", parent_asset_id="a", tenant_id="t", env="d", 
            kind="asr_transcript", uri=transcript_path,
            start_ms=0, end_ms=5000
        )
    ]
    
    mock_media.register_artifact.side_effect = lambda r: DerivedArtifact(id="x", parent_asset_id="a", tenant_id="t", env="d", kind="audio_phrase", uri="u")

    service = AudioVoicePhrasesService(media_service=mock_media)
    try:
        req = VoicePhraseDetectRequest(
            tenant_id="t1", env="dev", asset_id="a",
            max_gap_ms=2000
        )
        
        with patch("engines.audio_voice_phrases.service.check_dependencies") as mock_check:
            mock_check.return_value = _fake_dependencies(True)
            res = service.detect_phrases(req)
        assert len(res.phrases) == 1
        assert "Welcome to the jungle. We got fun" in res.phrases[0].transcript
    finally:
        if os.path.exists(transcript_path):
            os.unlink(transcript_path)


def test_detect_phrases_rejects_unknown_tenant():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="x", tenant_id="t", env="d", kind="audio", source_uri="u")
    mock_media.list_artifacts_for_asset.return_value = []
    mock_media.register_artifact.return_value = DerivedArtifact(id="x", parent_asset_id="x", tenant_id="t", env="d", kind="audio_phrase", uri="u")

    service = AudioVoicePhrasesService(media_service=mock_media)
    req = VoicePhraseDetectRequest(tenant_id="t_unknown", env="dev", asset_id="x")

    with patch("engines.audio_voice_phrases.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(True)
        with pytest.raises(ValueError):
            service.detect_phrases(req)


def test_detect_phrases_stub_backend_when_librosa_missing():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a", tenant_id="t", env="d", kind="audio", source_uri="u")
    mock_media.list_artifacts_for_asset.return_value = []
    mock_media.register_artifact.return_value = DerivedArtifact(id="phrase_stub", parent_asset_id="a", tenant_id="t", env="d", kind="audio_phrase", uri="u")

    service = AudioVoicePhrasesService(media_service=mock_media)
    req = VoicePhraseDetectRequest(tenant_id="t", env="d", asset_id="a")

    with patch("engines.audio_voice_phrases.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        res = service.detect_phrases(req)

    assert res.meta["backend_info"]["backend_type"] == "stub"
    assert len(res.phrases) == 1
    assert res.phrases[0].transcript == "stub phrase"
