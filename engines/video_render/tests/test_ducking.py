import pytest
from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_render.models import RenderRequest, RenderProfile, RenderPlan
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.media_v2.models import MediaAsset

@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_render_ducking_filter_gen(mock_gcs, mock_tl_svc, mock_media_svc):
    # Tests that _build_plan generates correct ducking filter expressions
    
    mock_media = mock_media_svc.return_value
    mock_media.get_asset.side_effect = lambda aid: MediaAsset(id=aid, tenant_id="t1", env="dev", kind="video", source_uri=f"/tmp/{aid}.mp4", duration_ms=60000)
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="DuckTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="Seq1")]
    
    # Tracks:
    # 1. Voice (Role="dialogue")
    # 2. Music (Role="music")
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0, meta={"audio_role": "dialogue"})
    t2 = Track(id="t2", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=1, meta={"audio_role": "music"})
    mock_tl.list_tracks_for_sequence.return_value = [t1, t2]
    
    # Clips:
    # Voice: 10s-20s on Timeline
    c1 = Clip(id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="v1", start_ms_on_timeline=10000, in_ms=0, out_ms=10000)
    # Music: 0s-30s on Timeline
    c2 = Clip(id="c2", track_id="t2", tenant_id="t1", env="dev", asset_id="m1", start_ms_on_timeline=0, in_ms=0, out_ms=30000)
    
    def list_clips(tid):
        if tid == "t1": return [c1]
        elif tid == "t2": return [c2]
        return []
    mock_tl.list_clips_for_track.side_effect = list_clips
    mock_tl.list_automation.return_value = []
    mock_tl.get_filter_stack_for_target.return_value = None

    svc = RenderService()
    
    req = RenderRequest(
        tenant_id="t1", env="dev", user_id="u1", project_id="p1",
        render_profile="preview_720p_fast",
        ducking={"atten_db": -12}
    )
    
    plan: RenderPlan = svc._build_plan(req)
    
    # Check Filters
    filters = ";".join(plan.filters)
    print(filters)
    
    # We expect Music Clip (c2) to have a volume filter with enable expression
    # Voice is 10s-20s. Render starts at 0.
    # So duck range: 10.0 to 20.0
    
    # Look for: volume=dB=-12:enable='between(t,10.000,20.000)'
    expected_expr = "volume=dB=-12:enable='between(t,10.000,20.000)'"
    
    assert expected_expr in filters
    
    # Check if filters are applied to separate chains
    # Voice Clip (idx 0? Sorted clips order?)
    # c2 (Music) starts at 0. c1 (Voice) starts at 10.
    # Sorted: c2, c1.
    # So c2 is first.
    # c2 filter chain should contain the ducking.
