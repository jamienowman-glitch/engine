import pytest
from unittest.mock import MagicMock, patch
from engines.video_focus_automation.models import FocusRequest
from engines.video_focus_automation.service import FocusAutomationService
from engines.media_v2.models import DerivedArtifact, MediaAsset

@patch("engines.video_focus_automation.service.get_media_service")
def test_focus_automation(mock_ms_getter):
    mock_ms = mock_ms_getter.return_value
    
    # Mock Asset
    mock_ms.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=20000, source_uri="/tmp/a1.mp4")
    
    art_audio = DerivedArtifact(
        id="aud1", tenant_id="t1", env="dev", parent_asset_id="a1", 
        kind="audio_semantic_timeline", uri="mem://a1",
        meta={"events": [{"kind": "speech", "start_ms": 5000, "end_ms": 10000}]}
    )
    art_visual = DerivedArtifact(
        id="vis1", tenant_id="t1", env="dev", parent_asset_id="a1", 
        kind="visual_meta", uri="vis://a1",
        meta={
            "frames": [
                {"timestamp_ms": 0, "primary_subject_center_x": 0.5, "primary_subject_center_y": 0.5},
                {"timestamp_ms": 5000, "primary_subject_center_x": 0.8, "primary_subject_center_y": 0.4},
                {"timestamp_ms": 10000, "primary_subject_center_x": 0.8, "primary_subject_center_y": 0.4},
            ]
        }
    )
    
    mock_ms.list_artifacts_for_asset.return_value = [art_audio, art_visual]
    mock_ms.get_artifact.side_effect = lambda aid: art_audio if aid == "aud1" else art_visual
    
    # Init Service
    svc = FocusAutomationService(media_service=mock_ms)
    
    # Request
    req = FocusRequest(clip_id="c1", asset_id="a1")
    res = svc.calculate_focus(req)
    
    assert res is not None
    kfs_x = res.automation_x.keyframes
    
    # Analyze Keyframes
    # Expect: 
    # 0ms -> 0.5 (initial)
    # 5000ms -> 0.8
    # 10000ms -> 0.8
    
    val_at_5s = next((k.value for k in kfs_x if k.time_ms == 5000), None)
    val_at_10s = next((k.value for k in kfs_x if k.time_ms == 10000), None)
    
    assert val_at_5s == pytest.approx(0.8)
    assert val_at_10s == pytest.approx(0.8)
    
    # Ensure they exist
    assert len(kfs_x) >= 3
