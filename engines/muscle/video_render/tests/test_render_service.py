import tempfile
from pathlib import Path

import pytest

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service, LocalMediaStorage
from engines.video_render.models import RenderRequest
from engines.video_render.service import set_render_service, RenderService
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.tests.helpers import make_video_render_client


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))


def test_render_dry_run_minimal():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    tmp_file = Path(tempfile.mkdtemp()) / "sample.wav"
    tmp_file.write_bytes(b"123")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(tmp_file))
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Render Demo"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    track = timeline_service.create_track(
        Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0)
    )
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )

    client = make_video_render_client()
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="social_1080p_h264", dry_run=True)
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"]
    assert body["plan_preview"]["output_path"]
    plan_meta = body["plan_preview"]["meta"]
    assert "encoder_used" in plan_meta
    assert plan_meta["source_assets"] == [asset.id]


def test_missing_asset_dry_run():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    
    # Register asset with non-existent path
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri="/non/existent/file.mp4")
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Missing Asset"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    track = timeline_service.create_track(
        Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0)
    )
    timeline_service.create_clip(
        Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=0)
    )
    
    # We must patch create_app injection or set global services
    # create_app uses get_media_service / get_timeline_service which look at global var
    # setup_module set them once, but here we can reset them or just use what setup_module did?
    # Actually setup_module sets one-time empty services. 
    # Let's override them for this test's data isolation.
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    client = make_video_render_client()
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="social_1080p_h264", dry_run=True)
    
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    body = resp.json()
    
    plan_meta = body["plan_preview"]["meta"]
    assert "render_warnings" in plan_meta
    # Should see "missing asset" in warnings
    warnings = plan_meta["render_warnings"]
    assert any("missing asset" in w for w in warnings)
    
    # Verify input meta has error detail
    input_meta = body["plan_preview"]["input_meta"]
    assert any(m.get("error") and "local asset not found" in m["error"] for m in input_meta)


def test_missing_asset_real_run():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri="/non/existent/real.mp4")
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Missing Real"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    track = timeline_service.create_track(
        Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0)
    )
    timeline_service.create_clip(
        Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=0)
    )
    
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    
    from engines.video_render.service import AssetAccessError
    service = RenderService()
    
    # We can't trigger via dry-run=False endpoint easily because create_app puts it into a job queue or async?
    # Actually RenderRequest usually goes to create_job which enqueues.
    # But checking if we have a synchronous way to test error.
    # service._build_plan calls _ensure_local, so if we call _build_plan via create_job (for dry run snapshot or even setup).
    # create_job -> _build_plan (for snapshot if dry_run=True, but here we want non-dry failure?)
    # create_job -> _build_plan(dry_run=True) for snapshot, so that won't fail (just Warns).
    # Then run_job calls _execute_plan... wait create_job builds a plan snapshot via dry_run logic.
    # The ACTUAL fail happens when `_execute_plan` runs `run_ffmpeg`.
    # But `_build_plan` constructs inputs.
    # If `create_job` calls `_build_plan` with `dry_run=True`, it swallows error and puts placeholder.
    # Then `run_job` -> `_execute_plan` uses that plan? 
    # NO. `jobs.py`/`service.py` logic:
    # A queued job has a `plan_snapshot`. Does execution use that? 
    # Usually `_execute_plan` takes a `RenderPlan`.
    # Let's checking `run_job` implementation later. 
    # Actually for this test, we can just call `service._build_plan(req_not_dry)` directly to prove it raises.
    
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="social_1080p_h264", dry_run=False)
    
    with pytest.raises(AssetAccessError, match="local asset not found"):
        service._build_plan(req)
