import pytest
from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_render.models import RenderRequest
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_render_stabilise(mock_gcs, mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/original.mp4", duration_ms=60000)
    mock_media.get_asset.return_value = asset
    
    # Stabilisation Transform Artifact
    trf_art = DerivedArtifact(
        id="art_trf", tenant_id="t1", env="dev", parent_asset_id="a1", 
        kind="video_stabilise_transform", uri="/tmp/transform.trf", meta={}
    )
    mock_media.list_artifacts_for_asset.return_value = [trf_art]
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="StabTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S1")]
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0)
    mock_tl.list_tracks_for_sequence.return_value = [t1]
    
    # Clip with customise=True
    c1 = Clip(
        id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", 
        start_ms_on_timeline=0, in_ms=0, out_ms=5000, 
        stabilise=True
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
    
    # Verify filter chain
    # Should contain vidstabtransform=input=...
    filters = "".join(plan.filters)
    assert "vidstabtransform" in filters
    assert "/tmp/transform.trf" in filters
    assert "smoothing=15" in filters
    stabilise_details = plan.meta.get("stabilise_details")
    assert stabilise_details
    assert stabilise_details[0]["clip_id"] == "c1"
    assert stabilise_details[0]["description"] == "Moderate smoothing with minimal crop"


@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_render_stabilise_warning_missing_transform(mock_gcs, mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/original.mp4", duration_ms=60000)
    mock_media.get_asset.return_value = asset
    mock_media.list_artifacts_for_asset.return_value = []
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="StabTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S1")]
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0)
    mock_tl.list_tracks_for_sequence.return_value = [t1]
    
    c1 = Clip(
        id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", 
        start_ms_on_timeline=0, in_ms=0, out_ms=5000, 
        stabilise=True
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
    
    assert "stabilise_warnings" in plan.meta
    assert plan.meta["stabilise_warnings"][0].startswith("stabilise_transform_missing_clip")
    assert "stabilise_details" not in plan.meta
