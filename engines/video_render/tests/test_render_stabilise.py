
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service, LocalMediaStorage
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.tests.helpers import make_video_render_client


def _setup_services():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())
    return media_service, timeline_service

def _create_project_with_stabilised_clip(media_service, timeline_service, stabilise=True, clip_meta=None, with_artifact=True):
    # Asset
    tmp_vid = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_vid.write_bytes(b"video")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_vid))
    )
    
    if with_artifact:
        trf_path = Path(tempfile.mkdtemp()) / "transform.trf"
        trf_path.write_bytes(b"dummy_data")
        media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id="t_test", env="dev", parent_asset_id=asset.id,
                kind="video_stabilise_transform", uri=str(trf_path),
                meta={"backend": "vidstab"}
            )
        )
    
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", title="Stab Test"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", sequence_id=sequence.id, kind="video", order=0))
    
    clip_kwargs = {
        "tenant_id": "t_test", "env": "dev", "track_id": track.id, "asset_id": asset.id, 
        "in_ms": 0, "out_ms": 2000, "start_ms_on_timeline": 0,
        "stabilise": stabilise
    }
    if clip_meta:
        clip_kwargs["meta"] = clip_meta
        
    clip = timeline_service.create_clip(Clip(**clip_kwargs))
    return project, clip

def test_stabilise_defaults():
    """Verify defaults are applied: smoothing=0.1, zoom=0, crop=black, tripod=0."""
    media, timeline = _setup_services()
    project, clip = _create_project_with_stabilised_clip(media, timeline, stabilise=True, with_artifact=True)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    plan_str = ";".join(plan["filters"])
    meta = plan["meta"]
    
    # Filter string check
    assert "vidstabtransform" in plan_str
    assert "smoothing=0.1" in plan_str
    assert "zoom=0" in plan_str
    assert "crop=black" in plan_str
    assert "tripod=0" in plan_str
    
    # Meta check
    assert "stabilise_details" in meta
    details = meta["stabilise_details"]
    assert len(details) == 1
    assert details[0]["clip_id"] == clip.id
    assert details[0]["smoothing"] == 0.1
    assert details[0]["crop"] == "black"

def test_stabilise_overrides():
    """Verify metadata can override defaults."""
    media, timeline = _setup_services()
    project, clip = _create_project_with_stabilised_clip(
        media, timeline, stabilise=True, with_artifact=True,
        clip_meta={"smoothing": 0.5, "crop": "keep", "zoom": 5}
    )
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    plan_str = ";".join(plan["filters"])
    
    assert "smoothing=0.5" in plan_str
    assert "crop=keep" in plan_str
    assert "zoom=5" in plan_str
    # Tripod should remain default
    assert "tripod=0" in plan_str

def test_stabilise_missing_artifact():
    """Verify warning if transform artifact is missing."""
    media, timeline = _setup_services()
    project, clip = _create_project_with_stabilised_clip(media, timeline, stabilise=True, with_artifact=False)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    plan_str = ";".join(plan["filters"])
    meta = plan["meta"]
    
    # No filter should be applied
    assert "vidstabtransform" not in plan_str
    
    # Warning check
    assert "render_warnings" in meta
    warnings = meta["render_warnings"]
    assert any("stabilise_transform_missing_clip" in w for w in warnings)
