import os
import json
import pytest
from unittest.mock import MagicMock, patch, mock_open
from engines.audio_voice_phrases.service import AudioVoicePhrasesService
from engines.audio_voice_phrases.models import VoicePhraseDetectRequest
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.audio_voice_phrases.service.get_media_service")
@patch("engines.audio_voice_phrases.service.GcsClient")
@patch("engines.audio_voice_phrases.service.shutil.which")
@patch("engines.audio_voice_phrases.service.subprocess.run")
@patch("engines.audio_voice_phrases.backend.open") # Mock backend open for reading transcript
def test_detect_phrases_real(mock_open_file, mock_run, mock_which, mock_gcs, mock_get_media):
    # Setup Mocks
    mock_media = mock_get_media.return_value
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/audio.wav")
    
    # Mock artifacts
    mock_media.list_artifacts_for_asset.return_value = [
        DerivedArtifact(id="art1", tenant_id="t1", env="dev", parent_asset_id="a1", kind="asr_transcript", uri="/tmp/trans.json")
    ]
    
    # Mock upload return
    mock_media.register_upload.return_value = MediaAsset(id="a2", tenant_id="t1", env="dev", kind="audio", source_uri="gs://bucket/slice.wav")
    
    # Mock artifact register return
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="p1", tenant_id="t1", env="dev", parent_asset_id="a1", kind="audio_phrase", uri="gs://bucket/slice.wav"
    )
    
    # Mock transcript content
    transcript_content = [
        {"word": "Hello", "start_ms": 1000, "end_ms": 1500, "conf": 0.9},
        {"word": "world", "start_ms": 1600, "end_ms": 2000, "conf": 0.8}, # Gap 100ms
        {"word": "Test",  "start_ms": 5000, "end_ms": 5500, "conf": 0.9}  # Gap 3000ms
    ]
    # mock_open requires a context manager setup
    file_mock = MagicMock()
    file_mock.__enter__.return_value = file_mock
    file_mock.read.return_value = json.dumps(transcript_content)
    mock_open_file.return_value = file_mock
    # We also need json.load to work on the mock file object. 
    # Usually json.load calls .read().
    # But patching built-in open is tricky across modules.
    # The backend imports open? No, built-in.
    
    # Mock GCS ensure local
    # Here source_uri is local, so it returns it directly.
    
    # Mock ffmpeg
    mock_which.return_value = "/usr/bin/ffmpeg"
    mock_run.return_value.returncode = 0
    
    with patch("engines.audio_voice_phrases.service.os.path.exists", return_value=True):
        with patch("engines.audio_voice_phrases.service.Path.read_bytes", return_value=b"FAKE_PHRASE_BYTES"):
            with patch("engines.audio_voice_phrases.service.Path.unlink", return_value=None):
                
                # Setup Service
                svc = AudioVoicePhrasesService(media_service=mock_media)
                req = VoicePhraseDetectRequest(tenant_id="t1", env="dev", asset_id="a1", max_gap_ms=500, min_phrase_len_ms=100)
                
                res = svc.detect_phrases(req)
                
                # Verify
                # Hello + world should merge (gap=100 <= 500)
                # Test should be separate
                assert len(res.phrases) == 2
                assert res.phrases[0].transcript == "Hello world"
                assert res.phrases[1].transcript == "Test"
                
                assert len(res.artifact_ids) == 2
                assert res.meta["engine"] == "audio_voice_phrases_v2"
                
                # Check backend detect called (implicit via result)
                
                # Check slicing
                assert mock_run.call_count == 2
                
                # Check upload used dummy source_uri
                assert mock_media.register_upload.call_count == 2
