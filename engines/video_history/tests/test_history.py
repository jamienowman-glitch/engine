import pytest
from unittest.mock import MagicMock, patch
from engines.video_history.service import HistoryService
from engines.video_timeline.models import Sequence, Track, Clip

@patch("engines.video_history.service.get_timeline_service")
def test_history_diff(mock_ts_getter):
    mock_ts = mock_ts_getter.return_value
    
    # Setup Mocks
    mock_ts.get_sequence.return_value = Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="Seq")
    mock_ts.list_tracks_for_sequence.return_value = [Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video")]
    
    # State 1: No Clips
    mock_ts.list_clips_for_track.return_value = []
    
    svc = HistoryService(timeline_service=mock_ts)
    snap1 = svc.snapshot("s1", "Empty")
    
    # State 2: One Clip Added
    c1 = Clip(id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0)
    mock_ts.list_clips_for_track.return_value = [c1]
    
    snap2 = svc.snapshot("s1", "Added Clip")
    
    # Diff
    diff = svc.diff(snap1.id, snap2.id)
    
    assert diff is not None
    assert len(diff.changes) == 1
    assert diff.changes[0].type == "ADD"
    assert diff.changes[0].target_id == "c1"
