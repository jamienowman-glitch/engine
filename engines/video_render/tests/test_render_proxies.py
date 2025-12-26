
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

import pytest

from engines.video_render.service import RenderService
from engines.video_render.jobs import InMemoryRenderJobRepository
from engines.media_v2.service import MediaService, set_media_service, InMemoryMediaRepository, LocalMediaStorage
from engines.video_timeline.service import TimelineService, set_timeline_service, InMemoryTimelineRepository
from engines.media_v2.models import MediaUploadRequest
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip

def setup_function():
    set_media_service(MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))

def _get_service():
    return RenderService(job_repo=InMemoryRenderJobRepository())

def _create_project_with_asset(media, timeline):
    tmp_vid = Path(tempfile.mkdtemp()) / "source.mp4"
    tmp_vid.write_bytes(b"dummy_video_content")
    
    asset = media.register_remote(
        MediaUploadRequest(tenant_id="t1", env="dev", user_id="u1", kind="video", source_uri=str(tmp_vid))
    )
    
    project = timeline.create_project(VideoProject(tenant_id="t1", env="dev", title="ProxyTest"))
    seq = timeline.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=project.id, name="S1"))
    track = timeline.create_track(Track(tenant_id="t1", env="dev", sequence_id=seq.id, kind="video"))
    clip = timeline.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=track.id, asset_id=asset.id, 
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    ))
    return project, asset

def test_proxy_generation_and_meta():
    """Verify proxy generation creates artifacts with correct metadata."""
    service = _get_service()
    meta_mock = MagicMock()
    # Mock execute_plan to return a dummy path without running ffmpeg
    with patch.object(service, "_execute_plan", return_value="/tmp/dummy_proxy.mp4") as mock_exec:
        # Mock upload to return a URI
        with patch.object(service, "_maybe_upload_output", return_value="file:///tmp/dummy_proxy.mp4"):
             # Mock hardware encoder resolution
             with patch.object(service, "_resolve_hardware_encoder", return_value="h264_mock"):
                project, asset = _create_project_with_asset(service.media_service, service.timeline_service)
                
                # First pass: should generate
                missing = service.ensure_proxies_for_project(project.id)
                # We expect non-zero generated (PROXY_LADDER has items)
                assert missing > 0
                assert mock_exec.called
                
                # Check artifacts
                artifacts = service.media_service.list_artifacts_for_asset(asset.id)
                assert len(artifacts) > 0
                
                # Verify metadata on the first artifact
                art = artifacts[0]
                assert "encoder_used" in art.meta
                assert art.meta["encoder_used"] == "h264_mock"
                assert "render_profile" in art.meta
                assert "source_asset_id" in art.meta
                assert art.meta["source_asset_id"] == asset.id
                assert "proxy_cache_key" in art.meta

def test_proxy_reuse():
    """Verify existing proxies are reused and not regenerated."""
    service = _get_service()
    
    with patch.object(service, "_execute_plan", return_value="/tmp/dummy_proxy.mp4") as mock_exec:
        with patch.object(service, "_maybe_upload_output", return_value="file:///tmp/dummy_proxy.mp4"):
             with patch.object(service, "_resolve_hardware_encoder", return_value="h264_mock"):
                project, asset = _create_project_with_asset(service.media_service, service.timeline_service)
                
                # First pass
                service.ensure_proxies_for_project(project.id)
                call_count_initial = mock_exec.call_count
                assert call_count_initial > 0
                
                # Second pass - should reuse
                missing = service.ensure_proxies_for_project(project.id)
                assert missing == 0
                
                # Call count should verify NO new calls were made
                # Note: ensure_proxies loops over ladder. If all exist, it skips generation.
                assert mock_exec.call_count == call_count_initial

def test_proxy_prefix_and_grouping():
    """Verify artifact grouping logic via cache keys."""
    service = _get_service()
    # Implicitly tested by reuse, but let's check cache key logic specifically
    project, asset = _create_project_with_asset(service.media_service, service.timeline_service)
    
    key1 = service._proxy_cache_key(asset, "video_proxy_360p")
    # Should contain asset id and source uri
    assert asset.id in key1
    assert str(asset.source_uri) in key1
    
    # If we modify asset source in meta (simulating a version change), key should change?
    # service._proxy_cache_key check: asset.meta.get("proxy_source") or asset.source_uri
    asset.meta["proxy_source"] = "new_version_hash"
    key2 = service._proxy_cache_key(asset, "video_proxy_360p")
    assert key1 != key2
