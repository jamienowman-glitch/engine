import pytest
from unittest.mock import MagicMock, patch
from engines.audio_performance_capture.service import AudioPerformanceCaptureService, CaptureRequest
from engines.audio_performance_capture.quantise import quantise_events
from engines.audio_performance_capture.models import PerformanceEvent
from engines.media_v2.models import DerivedArtifact

def test_detect_service_flow():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="u", meta={}
    )
    
    with patch("engines.audio_performance_capture.service.detect_onsets") as mock_detect:
        # 3 hits: 0ms, 510ms, 1020ms.
        # 120bpm -> beat=500ms.
        mock_detect.return_value = ([0.0, 510.0, 1020.0], [0.5, 0.5, 0.5])
        
        svc = AudioPerformanceCaptureService(media_service=mock_media)
        
        req = CaptureRequest(
            tenant_id="t", env="d", source_artifact_id="a1",
            target_bpm=120.0,
            humanise_blend=0.0 # Snap hard
        )
        
        res = svc.process_performance(req)
        
        assert len(res.events) == 3
        # 510 should snap to 500 (beat 1)
        # 1020 should snap to 1000 (beat 2)
        assert res.events[1].time_ms == 500.0
        assert res.events[2].time_ms == 1000.0

def test_quantise_logic():
    # 120bpm = 500ms/beat. 16th = 125ms.
    events = [PerformanceEvent(time_ms=120.0, velocity=1.0)] # Near 125
    
    # 1. Snap (blend 0)
    q1 = quantise_events(events, bpm=120, subdivision=16, humanise_blend=0.0)
    assert q1[0].time_ms == 125.0
    
    # 2. Original (blend 1)
    q2 = quantise_events(events, bpm=120, subdivision=16, humanise_blend=1.0)
    assert q2[0].time_ms == 120.0
    
    # 3. Blend 0.5 -> avg(125, 120) = 122.5
    q3 = quantise_events(events, bpm=120, subdivision=16, humanise_blend=0.5)
    assert q3[0].time_ms == 122.5
