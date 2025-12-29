
import pytest
from unittest.mock import MagicMock
from engines.video_assist.service import VideoAssistService

@pytest.fixture
def mock_timeline_service():
    return MagicMock()

@pytest.fixture
def mock_media_service():
    return MagicMock()

@pytest.fixture
def service(mock_timeline_service, mock_media_service):
    return VideoAssistService(
        timeline_service=mock_timeline_service,
        media_service=mock_media_service
    )

def test_generate_highlights_scoring(service, mock_timeline_service, mock_media_service):
    # Setup project
    project = MagicMock(tenant_id="t1", env="dev", sequence_ids=["sq1"])
    # MagicMock attributes behave like mocks unless set, but initializing with kwargs sets them?
    # Actually MagicMock(tenant_id="t1") sets it.
    mock_timeline_service.get_project.return_value = project
    mock_timeline_service.list_tracks_for_sequence.return_value = [MagicMock(kind="video", id="tk1")]
    mock_timeline_service.list_clips_for_track.return_value = [
        MagicMock(asset_id="speech_asset"),
        MagicMock(asset_id="silent_asset")
    ]
    
    # Mock Artifacts
    # speech_asset: has speech event (high score)
    art_speech = MagicMock()
    art_speech.kind = "audio_semantic_timeline"
    art_speech.meta = {
        "events": [{"kind": "speech", "start_ms": 0, "end_ms": 5000, "confidence": 0.9}]
    }
    
    # silent_asset: has silence event (ignored, score 0 -> fallback? No, filtering ignores it)
    # Actually if filtering ignores it, it gets NO semantic segments.
    # Logic: "for seg in semantic_segs: score = ..."
    # If no segments, it won't be added to candidate_segments from loop.
    # If candidate_segments is empty at end, it does fallback.
    # But speech_asset WILL contribute segments.
    # So silent_asset won't be in candidates unless we fallback?
    # Wait, if ANY asset has segments, we use them.
    # So silent_asset is excluded.
    
    art_silent = MagicMock()
    art_silent.kind = "audio_semantic_timeline"
    art_silent.meta = {
        "events": [{"kind": "silence", "start_ms": 0, "end_ms": 5000}]
    }

    def list_artifacts(aid):
        if aid == "speech_asset": return [art_speech]
        return [art_silent]
    
    mock_media_service.list_artifacts_for_asset.side_effect = list_artifacts
    
    seq, track, clips = service.generate_highlights("p1", target_duration_ms=10000)
    
    # Should only select speech_asset clips because silent_asset yields no segments
    assert len(clips) > 0
    for c in clips:
        assert c.asset_id == "speech_asset"

def test_generate_highlights_fallback(service, mock_timeline_service, mock_media_service):
    # No semantic data -> Fallback
    mock_timeline_service.get_project.return_value = MagicMock(
         tenant_id="t1", env="dev", sequence_ids=["sq1"]
    )
    mock_timeline_service.list_tracks_for_sequence.return_value = [MagicMock(kind="video", id="tk1")]
    mock_timeline_service.list_clips_for_track.return_value = [MagicMock(asset_id="a1")]
    
    mock_media_service.list_artifacts_for_asset.return_value = [] # No artifacts
    
    # Mock asset for duration check in fallback
    asset = MagicMock(duration_ms=10000)
    mock_media_service.get_asset.return_value = asset
    
    seq, track, clips = service.generate_highlights("p1")
    
    # Should have fallback clips
    assert len(clips) > 0
    assert clips[0].asset_id == "a1"

def test_caching_and_determinism(service, mock_timeline_service, mock_media_service):
    mock_timeline_service.get_project.return_value = MagicMock(
        tenant_id="t1", env="dev", sequence_ids=["sq1"]
    )
    mock_timeline_service.list_tracks_for_sequence.return_value = [MagicMock(kind="video", id="tk1")]
    mock_timeline_service.list_clips_for_track.return_value = [
        MagicMock(asset_id="a1"), MagicMock(asset_id="a2")
    ]
    
    # Both have identical speech segments
    art = MagicMock()
    art.kind = "audio_semantic_timeline"
    art.meta = {"events": [{"kind": "speech", "start_ms": 0, "end_ms": 5000}]}
    mock_media_service.list_artifacts_for_asset.return_value = [art]
    
    # Run once
    seq1, _, clips1 = service.generate_highlights("p1")
    
    # Run again
    seq2, _, clips2 = service.generate_highlights("p1")
    
    # Determinism: Same order of clips
    # a1 and a2 have same score. Sorting by asset_id means a1 then a2.
    assert [c.asset_id for c in clips1] == [c.asset_id for c in clips2]
    
    # Cache hit check (internal inspect)
    assert "p1:30000" in service._highlight_cache
