import pytest
from unittest.mock import MagicMock, patch
from engines.video_render.service import PROXY_LADDER, RenderService
from engines.video_render.models import RenderRequest
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_render_with_proxies(mock_gcs, mock_tl_svc, mock_media_svc):
    # Tests that _build_plan uses proxy URI if available and requested
    
    mock_media = mock_media_svc.return_value
    
    # Asset definition
    # Original URI: /tmp/original.mp4
    # Proxy URI: /tmp/proxy_360p.mp4
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/original.mp4", duration_ms=60000)
    mock_media.get_asset.return_value = asset
    
    # Artifacts
    proxy_art = DerivedArtifact(
        id="art1", tenant_id="t1", env="dev", parent_asset_id="a1", 
        kind="video_proxy_360p", uri="/tmp/proxy_360p.mp4", meta={}
    )
    mock_media.list_artifacts_for_asset.return_value = [proxy_art]
    
    # Timeline
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="ProxyTest")
    mock_tl.list_sequences_for_project.return_value = [Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S1")]
    t1 = Track(id="t1", sequence_id="s1", tenant_id="t1", env="dev", kind="video", order=0)
    mock_tl.list_tracks_for_sequence.return_value = [t1]
    c1 = Clip(id="c1", track_id="t1", tenant_id="t1", env="dev", asset_id="a1", start_ms_on_timeline=0, in_ms=0, out_ms=10000)
    mock_tl.list_clips_for_track.return_value = [c1]
    mock_tl.list_automation.return_value = []
    mock_tl.get_filter_stack_for_target.return_value = None

    svc = RenderService()
    
    # Case 1: no proxies
    req_std = RenderRequest(
        tenant_id="t1", env="dev", user_id="u1", project_id="p1",
        render_profile="preview_720p_fast", use_proxies=False
    )
    plan_std = svc._build_plan(req_std)
    assert "/tmp/original.mp4" in plan_std.inputs
    assert "/tmp/proxy_360p.mp4" not in plan_std.inputs
    
    # Case 2: use proxies
    req_proxy = RenderRequest(
        tenant_id="t1", env="dev", user_id="u1", project_id="p1",
        render_profile="preview_720p_fast", use_proxies=True
    )
    plan_proxy = svc._build_plan(req_proxy)
    assert "/tmp/proxy_360p.mp4" in plan_proxy.inputs
    assert "/tmp/original.mp4" not in plan_proxy.inputs

    # Case 3: use proxies but none available
    # Mock media service to return empty list
    mock_media.list_artifacts_for_asset.return_value = []
    plan_fallback = svc._build_plan(req_proxy)
    assert "/tmp/original.mp4" in plan_fallback.inputs


@patch("engines.video_render.service.get_media_service")
@patch("engines.video_render.service.get_timeline_service")
@patch("engines.video_render.service.GcsClient")
def test_ensure_proxies_generates_missing(mock_gcs, mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    mock_timeline = mock_tl_svc.return_value

    project = MagicMock()
    project.id = "p1"
    mock_timeline.get_project.return_value = project

    seq = MagicMock()
    seq.id = "seq1"
    mock_timeline.list_sequences_for_project.return_value = [seq]

    track = MagicMock()
    track.id = "t1"
    track.kind = "video"
    mock_timeline.list_tracks_for_sequence.return_value = [track]

    clip = MagicMock()
    clip.asset_id = "a1"
    mock_timeline.list_clips_for_track.return_value = [clip]
    mock_timeline.list_automation.return_value = []
    mock_timeline.get_filter_stack_for_target.return_value = None

    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/source.mp4")
    mock_media.get_asset.return_value = asset
    mock_media.list_artifacts_for_asset.return_value = []

    service = RenderService()
    service.timeline_service = mock_timeline
    service.media_service = mock_media

    with patch.object(RenderService, "_generate_proxy_for_asset") as mock_generate:
        mock_generate.return_value = DerivedArtifact(
            id="proxy1",
            parent_asset_id="a1",
            tenant_id="t1",
            env="dev",
            kind=PROXY_LADDER[0]["kind"],
            uri="/tmp/proxy.mp4",
            meta={"proxy_cache_key": "cache"},
        )
        count = service.ensure_proxies_for_project("p1")
        assert count == len(PROXY_LADDER)
        assert mock_generate.call_count == len(PROXY_LADDER)
