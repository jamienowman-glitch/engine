import pytest
from unittest.mock import MagicMock, patch
from engines.video_motifs.service import MotifService
from engines.video_timeline.models import Track, Clip

@patch("engines.video_motifs.service.get_timeline_service")
def test_extract_motif(mock_ts_getter):
    mock_ts = mock_ts_getter.return_value
    
    # Mock Tracks
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video")
    mock_ts.list_tracks_for_sequence.return_value = [t1]
    
    # Mock Clips
    # Clip starts at 5s, ends 15s.
    c1 = Clip(
        id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1",
        in_ms=0, out_ms=10000, start_ms_on_timeline=5000
    )
    mock_ts.list_clips_for_track.return_value = [c1]
    
    svc = MotifService(timeline_service=mock_ts)
    
    # Extract from 4s to 10s
    # Clip starts at 5s, so expected relative start = 1s (5 - 4)
    # Duration in range: 5s to 10s = 5s
    motif = svc.extract_motif("s1", 4000, 10000)
    
    assert motif is not None
    assert len(motif.clips) == 1
    mc = motif.clips[0]
    assert mc.relative_start_ms == 1000
    assert mc.duration_ms == 5000
