import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.service import get_render_service, set_render_service, RenderService
from engines.video_render.jobs import InMemoryRenderJobRepository
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))
    set_render_service(RenderService(job_repo=InMemoryRenderJobRepository()))


def seed_project():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService(job_repo=InMemoryRenderJobRepository()))

    vid = Path(tempfile.mkdtemp()) / "v.mp4"
    vid.write_bytes(b"video")
    asset = media_service.register_remote(MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(vid)))
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Job Demo"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=500, start_ms_on_timeline=0))
    return project


def test_render_job_run_and_cache():
    project = seed_project()
    client = TestClient(create_app())

    # Create job
    resp = client.post(
        "/video/render/jobs",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    job = resp.json()

    # Run job
    run_resp = client.post(f"/video/render/jobs/{job['id']}/run")
    assert run_resp.status_code == 200
    run_job = run_resp.json()
    assert run_job["status"] in {"succeeded", "failed"}

    # Create another job same project/profile, expect immediate success via cache
    resp2 = client.post(
        "/video/render/jobs",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp2.status_code == 200
    job2 = resp2.json()
    assert job2["render_cache_key"] == job["render_cache_key"]
    assert job2["status"] in {"succeeded", "queued"}


def test_render_job_backpressure():
    project = seed_project()
    service = get_render_service()
    service._max_concurrent_jobs = 1
    client = TestClient(create_app())
    resp = client.post(
        "/video/render/jobs",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    resp2 = client.post(
        "/video/render/jobs",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp2.status_code == 400
