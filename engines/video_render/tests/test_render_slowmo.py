import pytest
from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_render.models import RenderRequest
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.media_v2.models import MediaAsset

@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_render_slowmo(mock_gcs, mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/src.mp4", duration_ms=60000)
    mock_media.get_asset.return_value = asset
    mock_media.list_artifacts_for_asset.return_value = []
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="SlowTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S1")]
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0)
    mock_tl.list_tracks_for_sequence.return_value = [t1]
    
    # Clip with speed=0.5, optical_flow=True
    c1 = Clip(
        id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", 
        start_ms_on_timeline=0, in_ms=0, out_ms=5000, 
        speed=0.5, optical_flow=True
    )
    mock_tl.list_clips_for_track.return_value = [c1]
    mock_tl.list_automation.return_value = []
    mock_tl.get_filter_stack_for_target.return_value = None

    svc = RenderService()
    req = RenderRequest(
        tenant_id="t1", env="dev", user_id="u1", project_id="p1",
        render_profile="preview_720p_fast" 
        # preview_720p_fast might have 30fps.
    )
    plan = svc._build_plan(req)
    
    filters = "".join(plan.filters)
    assert "minterpolate" in filters
    assert "fps=30" in filters  # default profile fps
    assert "mi_mode=mci" in filters
    assert "slowmo_details" in plan.meta
    assert plan.meta["slowmo_details"][0]["method"] == "minterpolate"
    assert plan.meta["slowmo_details"][0]["quality"] == "high"
    assert plan.meta["slowmo_details"][0]["preset_description"] == "High-quality optical flow (AOBMC/BiDIR)"


@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_render_slowmo_tblend_fallback(mock_gcs, mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/src.mp4", duration_ms=60000)
    mock_media.get_asset.return_value = asset
    mock_media.list_artifacts_for_asset.return_value = []
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="SlowTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S1")]
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0)
    mock_tl.list_tracks_for_sequence.return_value = [t1]
    
    c1 = Clip(
        id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", 
        start_ms_on_timeline=0, in_ms=0, out_ms=5000, 
        speed=0.4, optical_flow=False
    )
    mock_tl.list_clips_for_track.return_value = [c1]
    mock_tl.list_automation.return_value = []
    mock_tl.get_filter_stack_for_target.return_value = None

    svc = RenderService()
    req = RenderRequest(
        tenant_id="t1", env="dev", user_id="u1", project_id="p1",
        render_profile="preview_720p_fast" 
    )
    plan = svc._build_plan(req)

    filters = "".join(plan.filters)
    assert "tblend" in filters
    assert plan.meta["slowmo_details"][0]["method"] == "tblend"
    assert plan.meta["slowmo_details"][0]["quality"] == "high"
