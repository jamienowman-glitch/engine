
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
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

def _create_project_with_slowmo_clip(media_service, timeline_service, quality="high", optical_flow=False):
    # Asset
    tmp_vid = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_vid.write_bytes(b"video")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_vid))
    )
    
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", title="Slowmo Test"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", sequence_id=sequence.id, kind="video", order=0))
    
    # Clip with slow speed (0.5x) to trigger slowmo
    clip = timeline_service.create_clip(
        Clip(
            tenant_id="t_test", env="dev", track_id=track.id, asset_id=asset.id, 
            in_ms=0, out_ms=2000, start_ms_on_timeline=0,
            speed=0.5, # Slow motion
            optical_flow=optical_flow,
            meta={"slowmo_quality": quality}
        )
    )
    return project, clip

def test_slowmo_preset_high():
    """Verify high quality uses minterpolate with MCI/AOBMC."""
    media, timeline = _setup_services()
    project, clip = _create_project_with_slowmo_clip(media, timeline, quality="high", optical_flow=True)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    plan_str = ";".join(plan["filters"])
    
    # Should contain minterpolate=fps=...:mi_mode=mci:mc_mode=aobmc
    assert "minterpolate" in plan_str
    assert "mi_mode=mci" in plan_str
    assert "mc_mode=aobmc" in plan_str

def test_slowmo_fallback_no_optical_flow():
    """Verify high quality falls back to tblend if optical_flow=False."""
    media, timeline = _setup_services()
    # optical_flow=False (default behavior even if not explicitly set, but passing explicity here)
    project, clip = _create_project_with_slowmo_clip(media, timeline, quality="high", optical_flow=False)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    plan_str = ";".join(plan["filters"])
    
    # Should NOT use minterpolate, should use tblend
    assert "minterpolate" not in plan_str
    assert "tblend" in plan_str

def test_slowmo_preset_fast():
    """Verify fast quality uses tblend even with optical_flow=True."""
    media, timeline = _setup_services()
    project, clip = _create_project_with_slowmo_clip(media, timeline, quality="fast", optical_flow=True)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    plan_str = ";".join(plan["filters"])
    
    assert "minterpolate" not in plan_str
    assert "tblend" in plan_str

def test_slowmo_details_meta():
    """Verify slowmo details are recorded in plan meta."""
    media, timeline = _setup_services()
    project, clip = _create_project_with_slowmo_clip(media, timeline, quality="medium", optical_flow=True)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    meta = resp.json()["plan_preview"]["meta"]
    
    assert "slowmo_details" in meta
    details = meta["slowmo_details"]
    assert len(details) == 1
    assert details[0]["clip_id"] == clip.id
    assert details[0]["quality"] == "medium"
    # Medium preset should map to minterpolate if optical_flow=True
    assert details[0]["method"] == "minterpolate"

def test_slowmo_fallback_warning():
    """Verify fallback to tblend emits a warning."""
    media, timeline = _setup_services()
    # High quality + No optical flow -> Fallback
    project, clip = _create_project_with_slowmo_clip(media, timeline, quality="high", optical_flow=False)
    
    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    meta = resp.json()["plan_preview"]["meta"]
    
    # Check for warning
    assert "render_warnings" in meta
    warnings = meta["render_warnings"]
    assert any("slowmo_optical_flow_missing_fallback_tblend" in w for w in warnings)
    
