from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_render.models import RenderRequest, RenderProfile
from engines.video_timeline.models import FilterStack, Filter, VideoProject, Sequence, Track, Clip
from engines.media_v2.models import DerivedArtifact, MediaAsset

@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.run_ffmpeg")
@patch("engines.video_render.extensions.resolve_region_masks_for_clip")
def test_render_with_face_blur(mock_resolve, mock_ffmpeg, mock_timeline_svc, mock_media_svc):
    # Setup Services
    mock_timeline = mock_timeline_svc.return_value
    mock_media = mock_media_svc.return_value
    
    # Setup Timeline Data
    p = VideoProject(id="p1", tenant_id="t1", env="dev", title="test", project_id="p1")
    s = Sequence(id="s1", project_id="p1", duration_ms=10000, tenant_id="t1", env="dev", name="s1")
    t = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video")
    c = Clip(id="c1", track_id="t1", asset_id="a1", duration_ms=5000, start_ms_on_timeline=0, in_ms=0, out_ms=5000, tenant_id="t1", env="dev")
    
    mock_timeline.get_project.return_value = p
    mock_timeline.list_sequences_for_project.return_value = [s]
    mock_timeline.list_tracks_for_sequence.return_value = [t]
    mock_timeline.list_clips_for_track.return_value = [c]
    mock_timeline.list_automation.return_value = []
    
    # Asset
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/vid.mp4", duration_ms=10000)
    
    # Filter Stack: Face Blur
    f_blur = Filter(type="face_blur", params={"strength": 0.8}, enabled=True)
    stack = FilterStack(tenant_id="t1", env="dev", target_type="clip", target_id="c1", filters=[f_blur])
    mock_timeline.get_filter_stack_for_target.return_value = stack
    
    # Mock Region Resolution -> Find a mask
    mock_resolve.return_value = {0: "/tmp/mask_face.png"} # Filter index 0 -> mask uri
    
    # Run
    svc = RenderService()
    req = RenderRequest(tenant_id="t1", env="dev", user_id="u1", project_id="p1", render_profile="preview_720p_fast")
    
    plan = svc._build_plan(req)
    
    # Verify Plan
    # Inputs: Video + Mask
    assert len(plan.inputs) >= 2
    assert "/tmp/mask_face.png" in plan.inputs
    
    # Filters
    # Should see split, boxblur, alphamerge, overlay
    # Check for boxblur
    found_blur = any("boxblur=" in f for f in plan.filters)
    assert found_blur, "Expected boxblur filter in graph"
    
    # Check for alphamerge
    found_merge = any("alphamerge" in f for f in plan.filters)
    assert found_merge, "Expected alphamerge filter in graph"
    
    print(plan.filters)
