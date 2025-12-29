
import pytest
from unittest.mock import MagicMock, patch

from engines.video_preview.models import PreviewRequest
from engines.video_preview.service import PreviewService
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage, set_media_service
from engines.video_timeline.service import TimelineService, InMemoryTimelineRepository, set_timeline_service
from engines.video_render.service import RenderService
from engines.media_v2.models import MediaUploadRequest, DerivedArtifact
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip

def test_preview_proxy_enforcement_missing():
    # Setup mocks
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    
    # Inject globally so RenderService picks them up
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    
    render_service = RenderService()
    render_service.message_bus = MagicMock()
    # Mock ensure proxies
    render_service.ensure_proxies_for_project = MagicMock(return_value=0)
    
    # Create data
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t1", env="dev", user_id="u1", kind="video", source_uri="file:///tmp/source.mp4")
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t1", env="dev", title="P1"))
    seq = timeline_service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=project.id, name="S1"))
    track = timeline_service.create_track(Track(tenant_id="t1", env="dev", sequence_id=seq.id, kind="video"))
    clip = timeline_service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=track.id, asset_id=asset.id, 
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    ))
    
    svc = PreviewService(render_service=render_service, timeline_service=timeline_service)
    
    # We need render_service to return a dummy plan 
    # Mock render_service.render -> returns result with plan_preview
    mock_res = MagicMock()
    mock_res.plan_preview = MagicMock()
    mock_res.plan_preview.model_dump.return_value = {}
    mock_res.plan_preview.meta = {} # Must be dict
    mock_res.plan_preview.profile = "preview_720p_fast"
    render_service.render = MagicMock(return_value=mock_res)

    req = PreviewRequest(sequence_id=seq.id, strategy="DRAFT")
    
    # Run - NO PROXY ARTIFACT created yet
    res = svc.get_preview_stream(req)
    
    # Verify warning
    assert "preview_warnings" in mock_res.plan_preview.meta
    warnings = mock_res.plan_preview.meta["preview_warnings"]
    assert any("missing_proxy_for_clip" in w for w in warnings)

def test_preview_proxy_enforcement_present():
    # Setup mocks
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    
    render_service = RenderService()
    render_service.ensure_proxies_for_project = MagicMock(return_value=0)
    
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t1", env="dev", user_id="u1", kind="video", source_uri="file:///tmp/source.mp4")
    )
    # CREATE PROXY ARTIFACT
    media_service.repo.create_artifact(
        DerivedArtifact(
             id="art1", tenant_id="t1", env="dev", parent_asset_id=asset.id,
             kind="video_proxy_360p", uri="file:///tmp/proxy.mp4"
        )
    )
    
    project = timeline_service.create_project(VideoProject(tenant_id="t1", env="dev", title="P1"))
    seq = timeline_service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=project.id, name="S1"))
    track = timeline_service.create_track(Track(tenant_id="t1", env="dev", sequence_id=seq.id, kind="video"))
    clip = timeline_service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=track.id, asset_id=asset.id, 
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    ))
    
    svc = PreviewService(render_service=render_service, timeline_service=timeline_service)
    
    # Mock render result
    mock_res = MagicMock()
    mock_res.plan_preview = MagicMock()
    mock_res.plan_preview.model_dump.return_value = {}
    mock_res.plan_preview.meta = {}
    mock_res.plan_preview.profile = "preview_720p_fast"
    render_service.render = MagicMock(return_value=mock_res)

    req = PreviewRequest(sequence_id=seq.id, strategy="DRAFT")
    
    # Run
    res = svc.get_preview_stream(req)
    
    # Verify NO warnings (meta might have 'preview_warnings' key but empty or generic 'no_tracks' check passed)
    # The 'missing_proxy' warning should NOT be present
    if "preview_warnings" in mock_res.plan_preview.meta:
         warnings = mock_res.plan_preview.meta["preview_warnings"]
         assert not any("missing_proxy_for_clip" in w for w in warnings)

def test_preview_profile_selection():
     # DRAFT -> draft_480p_fast
     
     media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
     timeline_service = TimelineService(repo=InMemoryTimelineRepository())
     
     set_media_service(media_service)
     set_timeline_service(timeline_service)
     
     render_service = RenderService()
     render_service.ensure_proxies_for_project = MagicMock()
     render_service.render = MagicMock()
     
     mock_res = MagicMock()
     mock_res.plan_preview = MagicMock()
     mock_res.plan_preview.model_dump.return_value = {}
     mock_res.plan_preview.meta = {}
     mock_res.plan_preview.profile = "draft_480p_fast"
 
     render_service.render.return_value = mock_res
     
     project = timeline_service.create_project(VideoProject(tenant_id="t1", env="dev", title="P1"))
     seq = timeline_service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=project.id, name="S1"))
     
     svc = PreviewService(render_service=render_service, timeline_service=timeline_service)
     req = PreviewRequest(sequence_id=seq.id, strategy="DRAFT")
     
     svc.get_preview_stream(req)
     
     # Verify render called with validation profile
     # We expect backend_profile="draft_480p_fast"
     assert render_service.render.called
     args = render_service.render.call_args[0][0] # RenderRequest
     assert args.render_profile == "draft_480p_fast"
     assert args.use_proxies is True
     assert args.dry_run is True
     
