
import pytest
from unittest.mock import MagicMock
from engines.video_multicam.service import MultiCamService, PACING_PRESETS
from engines.video_multicam.models import (
    MultiCamSession, MultiCamTrackSpec, MultiCamAutoCutRequest
)

@pytest.fixture
def mock_media_service():
    return MagicMock()

@pytest.fixture
def mock_timeline_service():
    return MagicMock()

@pytest.fixture
def service(mock_media_service, mock_timeline_service):
    svc = MultiCamService(
        media_service=mock_media_service,
        timeline_service=mock_timeline_service
    )
    svc.gcs = None
    return svc

def test_auto_cut_pacing_constraints(service, mock_media_service, mock_timeline_service, monkeypatch):
    # Setup session
    session = MultiCamSession(
        id="s1", tenant_id="t1", env="dev", name="S1",
        tracks=[MultiCamTrackSpec(asset_id="a1")]
    )
    service.repo.create(session)
    
    # Mock asset
    asset = MagicMock(duration_ms=20000)
    mock_media_service.get_asset.return_value = asset
    
    # Force 'fast' pacing
    monkeypatch.setenv("VIDEO_MULTICAM_PACING_PRESET", "fast")
    
    req = MultiCamAutoCutRequest(
        tenant_id="t1", env="dev", session_id="s1"
    )
    
    # Mock timeline creation
    mock_timeline_service.create_sequence.return_value = MagicMock(id="seq1")
    mock_timeline_service.create_track.return_value = MagicMock(id="trk1")
    
    result = service.auto_cut_sequence(req)
    
    assert result.meta["pacing_preset"] == "fast"
    
    # Verify clip calls respect fast pacing (approx 1000-4000)
    # We can check create_clip calls
    calls = mock_timeline_service.create_clip.call_args_list
    assert len(calls) > 0
    for call in calls:
        clip = call[0][0] # first arg is Clip object
        dur = clip.out_ms - clip.in_ms
        assert dur <= PACING_PRESETS["fast"]["max"]
        assert dur >= PACING_PRESETS["fast"]["min"]

def test_auto_cut_semantic_selection(service, mock_media_service, mock_timeline_service):
    # Two cameras. Cam1 silent. Cam2 speaking.
    # Should pick Cam2.
    
    session = MultiCamSession(
        id="s_sem", tenant_id="t1", env="dev", name="Semantic",
        tracks=[
            MultiCamTrackSpec(asset_id="cam1", role="secondary"),
            MultiCamTrackSpec(asset_id="cam2", role="secondary")
        ]
    )
    service.repo.create(session)
    
    mock_media_service.get_asset.return_value = MagicMock(duration_ms=10000)
    
    # Cam1 artifacts: Silence
    art1 = MagicMock()
    art1.kind = "audio_semantic_timeline"
    art1.meta = {"events": [{"kind": "silence", "start_ms": 0, "end_ms": 10000}]}
    
    # Cam2 artifacts: Speech
    art2 = MagicMock()
    art2.kind = "audio_semantic_timeline"
    art2.meta = {"events": [{"kind": "speech", "start_ms": 0, "end_ms": 10000}]}
    
    def list_artifacts(aid):
        if aid == "cam1": return [art1]
        if aid == "cam2": return [art2]
        return []
        
    mock_media_service.list_artifacts_for_asset.side_effect = list_artifacts
    
    # Timeline stubs
    mock_timeline_service.create_sequence.return_value = MagicMock(id="seq1")
    mock_timeline_service.create_track.return_value = MagicMock(id="trk1")
    
    req = MultiCamAutoCutRequest(tenant_id="t1", env="dev", session_id="s_sem")
    service.auto_cut_sequence(req)
    
    # Verify clips are mostly Cam2
    calls = mock_timeline_service.create_clip.call_args_list
    cam2_count = sum(1 for c in calls if c[0][0].asset_id == "cam2")
    cam1_count = sum(1 for c in calls if c[0][0].asset_id == "cam1")
    
    assert cam2_count > cam1_count
