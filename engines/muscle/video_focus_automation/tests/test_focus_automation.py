
import pytest
from unittest.mock import MagicMock
from engines.video_focus_automation.service import FocusAutomationService
from engines.video_focus_automation.models import FocusRequest

@pytest.fixture
def mock_media_service():
    return MagicMock()

@pytest.fixture
def service(mock_media_service):
    # Mock GCS checks
    s = FocusAutomationService(media_service=mock_media_service)
    s.gcs = None 
    return s

def test_focus_success(service, mock_media_service):
    # Setup Asset
    asset = MagicMock(id="a1", tenant_id="t1", env="dev")
    mock_media_service.get_asset.return_value = asset
    
    # Setup Requests
    req = FocusRequest(
        clip_id="c1", asset_id="a1", tenant_id="t1", env="dev",
        audio_artifact_id="art_audio", visual_artifact_id="art_visual"
    )
    
    # Setup Artifact Content Mocking
    # We mock _load_artifact_json (private) or mocked artifact retrieval?
    # service._load_artifact_json calls get_artifact then _load. 
    # Let's mock _load_artifact_json directly if possible? 
    # Or just mock get_artifact return value with payload in meta.
    
    # Audio: Speech 1000-2000
    art_audio = MagicMock(id="art_audio")
    art_audio.meta = {"payload": {
        "events": [{"kind": "speech", "start_ms": 1000, "end_ms": 2000}]
    }}
    
    # Visual: Face at x=0.8, y=0.8 at t=1500
    art_visual = MagicMock(id="art_visual")
    art_visual.meta = {"payload": {
        "frames": [
            {"timestamp_ms": 1500, "primary_subject_center_x": 0.8, "primary_subject_center_y": 0.8}
        ]
    }}
    
    def get_art(aid):
        if aid == "art_audio": return art_audio
        if aid == "art_visual": return art_visual
        return None
    mock_media_service.get_artifact.side_effect = get_art
    
    # Execute
    res = service.calculate_focus(req)
    
    assert res is not None
    assert res.clip_id == "c1"
    
    # Check X Automation
    # Expect 0 (0.5), 1000 (0.8), 2000 (0.8)
    kfs = res.automation_x.keyframes
    assert len(kfs) >= 3
    # First is init 0
    assert kfs[0].value == 0.5
    
    # Find keyframe at 1000 or 2000
    kf_speech = next((k for k in kfs if k.time_ms == 1000), None)
    assert kf_speech is not None
    assert kf_speech.value == 0.8
    
    # Check Metadata
    assert res.meta["source_audio_artifact"] == "art_audio"

def test_focus_fallback(service, mock_media_service):
    asset = MagicMock(id="a1", tenant_id="t1", env="dev")
    mock_media_service.get_asset.return_value = asset
    
    # Req with no artifacts
    req = FocusRequest(clip_id="c1", asset_id="a1", tenant_id="t1", env="dev")
    mock_media_service.list_artifacts_for_asset.return_value = []
    
    res = service.calculate_focus(req)
    
    assert res is not None
    # Center crop default
    assert res.automation_x.keyframes[0].value == 0.5
    assert len(res.automation_x.keyframes) == 1

def test_focus_tenant_mismatch(service, mock_media_service):
    asset = MagicMock(id="a1", tenant_id="t1", env="dev")
    mock_media_service.get_asset.return_value = asset
    
    # Req with mismatch
    req = FocusRequest(clip_id="c1", asset_id="a1", tenant_id="t2", env="dev")
    
    with pytest.raises(ValueError, match="Access Denied"):
        service.calculate_focus(req)
