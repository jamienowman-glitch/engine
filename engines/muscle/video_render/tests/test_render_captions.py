import pytest
from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_render.models import RenderRequest
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
@patch("engines.video_render.service.get_captions_service")
def test_render_captions_burn_in(mock_cap_svc, mock_gcs, mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/src.mp4", duration_ms=60000)
    mock_media.get_asset.return_value = asset
    
    # Mock Captions Service
    mock_cap = mock_cap_svc.return_value
    # convert_to_srt should return a local path
    mock_cap.convert_to_srt.return_value = "/tmp/captions.srt"
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="CapTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S1")]
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0)
    mock_tl.list_tracks_for_sequence.return_value = [t1]
    
    # Clip
    c1 = Clip(
        id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", 
        start_ms_on_timeline=0, in_ms=0, out_ms=5000
    )
    mock_tl.list_clips_for_track.return_value = [c1]
    mock_tl.list_automation.return_value = []
    mock_tl.list_transitions_for_sequence.return_value = []
    mock_tl.get_filter_stack_for_target.return_value = None

    svc = RenderService()
    req = RenderRequest(
        tenant_id="t1", env="dev", user_id="u1", project_id="p1",
        render_profile="preview_720p_fast",
        burn_in_captions={"artifact_id": "art_transcript_1"}
    )
    plan = svc._build_plan(req)
    
    filters = "".join(plan.filters)
    assert "subtitles=filename='/tmp/captions.srt'" in filters
    
    # Verify we called convert_to_srt with the right artifact id
    mock_cap.convert_to_srt.assert_called_with("art_transcript_1")
