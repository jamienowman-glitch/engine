import pytest
from unittest.mock import MagicMock, patch
import os
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from engines.video_captions.backend import StubAsrBackend
from engines.video_captions.routes import router
from engines.video_captions.service import VideoCaptionsService, TranscriptSegment
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.video_captions.service.get_media_service")
@patch("engines.video_captions.service.GcsClient")
def test_captions_generation(mock_gcs_cls, mock_media_svc):
    # Setup GCS Mock
    mock_gcs = mock_gcs_cls.return_value
    mock_gcs.upload_raw_media.return_value = "gs://bucket/path.json"

    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/audio.wav")
    mock_media.get_asset.return_value = asset
    
    # Mock register_artifact
    def side_effect_register(req):
        return DerivedArtifact(
            id="art1", tenant_id=req.tenant_id, env=req.env, parent_asset_id=req.parent_asset_id,
            kind=req.kind, uri=req.uri, meta=req.meta
        )
    mock_media.register_artifact.side_effect = side_effect_register
    
    with patch.dict(os.environ, {"VIDEO_CAPTIONS_BACKEND": "stub", "VIDEO_CAPTIONS_LANGUAGE": "en"}):
        svc = VideoCaptionsService()
        art = svc.generate_captions("a1", language="en")

    assert art.kind == "asr_transcript"
    assert art.uri == "gs://bucket/path.json"
    assert art.meta["backend_version"] == StubAsrBackend.backend_version
    assert art.meta["model_used"] == StubAsrBackend.model_used
    assert art.meta["backend_type"] == "stub"
    assert art.meta["language"] == "en"
    assert art.meta["duration_ms"] == 0.0
    assert art.meta["segment_count"] == 3
    assert art.meta["cache_key"].startswith("a1|en|")

    # Verify upload was called
    mock_gcs.upload_raw_media.assert_called_once()
    call_args = mock_gcs.upload_raw_media.call_args
    local_path = call_args[0][2]
    assert os.path.exists(local_path)
    
    # Optional: Verify content of that json
    with open(local_path, 'r') as f:
        data = json.load(f)
        assert len(data) == 3
        assert data[0]["text"] == "Hello world."

@patch("engines.video_captions.service.get_media_service")
@patch("engines.video_captions.service.GcsClient")
def test_captions_srt_conversion(mock_gcs_cls, mock_media_svc):
    # Setup GCS mock to not crash and return local path
    mock_gcs = mock_gcs_cls.return_value
    mock_gcs.upload_raw_media.side_effect = lambda t, b, p: str(p)
    
    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/audio.wav")
    mock_media.get_asset.return_value = asset
    
    svc = VideoCaptionsService()
    
    # Manually create a transcript file for testing convert independently of generate
    transcript = [
        {"start": 0.0, "end": 1.5, "text": "Hello world"},
        {"start": 2.0, "end": 4.0, "text": "Testing SRT"}
    ]
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(transcript, f)
        json_path = f.name
        
    art = DerivedArtifact(
        id="art1", tenant_id="t1", env="dev", parent_asset_id="a1",
        kind="asr_transcript", uri=json_path, meta={}
    )
    mock_media.get_artifact.return_value = art
    
    srt_path = svc.convert_to_srt("art1")
    assert os.path.exists(srt_path)
    with open(srt_path, 'r') as f:
        content = f.read()
        
    # Check SRT format
    # 1
    # 00:00:00,000 --> 00:00:01,500
    # Hello world
    #
    # 2
    # 00:00:02,000 --> 00:00:04,000
    # Testing SRT
    
    assert "1" in content
    assert "00:00:00,000 --> 00:00:01,500" in content
    assert "Hello world" in content
    assert "Testing SRT" in content


def test_captions_srt_route():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    with patch("engines.video_captions.routes.get_captions_service") as mock_get:
        svc = MagicMock()
        svc.convert_to_srt.return_value = "/tmp/test.srt"
        mock_get.return_value = svc
        resp = client.get("/video/captions/art123/srt", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["srt_path"] == "/tmp/test.srt"
