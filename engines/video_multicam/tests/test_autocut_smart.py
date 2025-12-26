
import pytest
from unittest.mock import MagicMock
from engines.video_multicam.service import MultiCamService

@pytest.fixture
def service():
    # Minimal service wrapper to test private scoring methods
    # Mock media_service to avoid S3MediaStorage init error
    mock_media = MagicMock()
    svc = MultiCamService(media_service=mock_media)
    svc.gcs = None
    return svc

def test_semantic_energy_speech_overlap(service):
    # Mock artifact info
    # Window 0-1000ms
    # Speech event 200-800ms (600ms overlap) -> 0.6 coverage
    # Score = min(1.0, 0.6 * 1.5) = 0.9
    
    artifact = MagicMock()
    artifact.kind = "audio_semantic_timeline"
    artifact.meta = {
        "events": [
            {"kind": "speech", "start_ms": 200, "end_ms": 800},
            {"kind": "silence", "start_ms": 800, "end_ms": 1000}
        ]
    }
    
    info = {"artifacts": [artifact]}
    
    score = service._semantic_energy(info, 0, 1000)
    assert abs(score - 0.9) < 1e-5

def test_semantic_energy_no_speech(service):
    artifact = MagicMock()
    artifact.kind = "audio_semantic_timeline"
    artifact.meta = {
        "events": [
            {"kind": "silence", "start_ms": 0, "end_ms": 1000}
        ]
    }
    
    info = {"artifacts": [artifact]}
    
    score = service._semantic_energy(info, 0, 1000)
    assert score == 0.0

def test_semantic_energy_missing_artifact(service):
    info = {"artifacts": []}
    score = service._semantic_energy(info, 0, 1000)
    # Fallback is 0.0
    assert score == 0.0

def test_visual_motion_score_frames(service):
    # Window 0-1000
    # Frame at 500: score 0.8
    # Frame at 600: score 0.4
    # Avg = 0.6
    
    artifact = MagicMock()
    artifact.kind = "visual_meta"
    artifact.meta = {
        "frames": [
            {"timestamp_ms": 500, "motion_score": 0.8},
            {"timestamp_ms": 600, "motion_score": 0.4}
        ]
    }
    info = {"artifacts": [artifact]}
    
    score = service._visual_motion_score(info, 0, 1000)
    assert abs(score - 0.6) < 1e-5

def test_visual_motion_fallback_no_artifact(service):
    info = {"artifacts": []}
    # Fallback 0.2
    score = service._visual_motion_score(info, 0, 1000)
    assert score == 0.2

def test_visual_motion_fallback_property_name(service):
    # Old property name support
    artifact = MagicMock()
    artifact.kind = "visual_meta"
    artifact.meta = {
        "frames": [
            {"timestamp_ms": 500, "primary_subject_movement": 0.9}
        ]
    }
    info = {"artifacts": [artifact]}
    
    score = service._visual_motion_score(info, 0, 1000)
    assert score == 0.9
