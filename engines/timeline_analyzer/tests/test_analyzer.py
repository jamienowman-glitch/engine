import pytest
from unittest.mock import MagicMock, patch
from engines.timeline_analyzer.service import TimelineAnalyzerService
from engines.video_timeline.models import Sequence, Track, Clip

@patch("engines.timeline_analyzer.service.get_timeline_service")
def test_analyzer_complexity(mock_ts_getter):
    mock_ts = mock_ts_getter.return_value
    
    # Mock Sequence
    seq = Sequence(
        id="seq1", project_id="p1", tenant_id="t1", env="dev", name="ComplexSeq"
    )
    mock_ts.get_sequence.return_value = seq
    
    # Mock Tracks (Just 1 track or multiple doesn't strictly matter for clip density if we check all clips)
    # But usually clips are on tracks.
    tracks = [Track(id=f"t{i}", sequence_id="seq1", tenant_id="t1", env="dev", kind="video") for i in range(8)]
    mock_ts.list_tracks_for_sequence.return_value = tracks
    
    # Mock Clips: Each track has 1 clip from 0s to 10s
    # So overlap at t=5s is 8.
    def list_clips(tid):
        return [Clip(
            id=f"c_{tid}", track_id=tid, tenant_id="t1", env="dev", asset_id="a1",
            in_ms=0, out_ms=10000, start_ms_on_timeline=0
        )]
    mock_ts.list_clips_for_track.side_effect = list_clips
    
    svc = TimelineAnalyzerService(timeline_service=mock_ts)
    report = svc.analyze("seq1")
    
    assert report is not None
    assert report.overall_status == "WARNING"
    
    # Check Density Metric
    density_metric = next((m for m in report.metrics if m.name == "Max Overlap"), None)
    assert density_metric is not None
    assert density_metric.value == 8
    assert density_metric.status == "WARNING"
    
    # Check messages
    assert any("Max Overlap is high" in msg for msg in report.messages)

@patch("engines.timeline_analyzer.service.get_timeline_service")
def test_analyzer_empty(mock_ts_getter):
    mock_ts = mock_ts_getter.return_value
    mock_ts.get_sequence.return_value = Sequence(id="seq2", project_id="p2", tenant_id="t1", env="dev", name="Empty")
    mock_ts.list_tracks_for_sequence.return_value = []
    
    svc = TimelineAnalyzerService(timeline_service=mock_ts)
    report = svc.analyze("seq2")
    
    assert report.overall_status == "CRITICAL"
    assert "Sequence is empty" in report.messages[0]
