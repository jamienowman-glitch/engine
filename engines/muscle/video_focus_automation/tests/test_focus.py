import pytest
import json
import os
from unittest.mock import MagicMock, patch
from engines.video_focus_automation.service import FocusAutomationService
from engines.video_focus_automation.models import FocusRequest
from engines.media_v2.models import DerivedArtifact, MediaAsset

def test_calculate_focus_logic():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=10000, source_uri="gs://foo")
    
    # Mock Artifacts
    mock_media.get_artifact.side_effect = lambda aid: DerivedArtifact(
        id=aid, parent_asset_id="a1", tenant_id="t1", env="dev", 
        kind="audio_semantic_timeline" if "audio" in aid else "visual_meta", 
        uri=f"/tmp/{aid}.json"
    )
    
    svc = FocusAutomationService(media_service=mock_media)
    
    # Synthetic Data
    audio_data = {
        "events": [
            {"kind": "speech", "start_ms": 1000, "end_ms": 2000}
        ]
    }
    
    visual_data = {
        "frames": [
            {"timestamp_ms": 1100, "primary_subject_center_x": 0.2, "primary_subject_center_y": 0.5},
            {"timestamp_ms": 1900, "primary_subject_center_x": 0.3, "primary_subject_center_y": 0.5},
            {"timestamp_ms": 5000, "primary_subject_center_x": 0.9, "primary_subject_center_y": 0.9} # Irrelevant time
        ]
    }
    
    # Mock File Reading
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", new_callable=MagicMock) as mock_open:
        
        # We need mock_open to return different content based on filename
        # This is tricky with mock_open.
        # Alternatively, patch _load_artifact_content?
        pass
        
    with patch.object(FocusAutomationService, "_load_artifact_content") as mock_load:
        def load_effect(art):
            if art.id == "art_audio": return audio_data
            if art.id == "art_visual": return visual_data
            return None
        mock_load.side_effect = load_effect
        
        req = FocusRequest(
            clip_id="c1", 
            asset_id="a1",
            audio_artifact_id="art_audio",
            visual_artifact_id="art_visual"
        )
        
        res = svc.calculate_focus(req)
        
        assert res is not None
        assert len(res.automation_x.keyframes) >= 2
        
        # Check generated values
        # Average center of 0.2 and 0.3 is 0.25
        # The keyframes at 1000ms and 2000ms should have value 0.25
        
        kfs = res.automation_x.keyframes
        # Find kf at 1000
        kf_1s = next(k for k in kfs if k.time_ms == 1000)
        assert kf_1s.value == pytest.approx(0.25)
