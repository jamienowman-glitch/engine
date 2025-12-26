import tempfile
import types
from pathlib import Path

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.jobs import InMemoryRenderJobRepository
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.tests.helpers import make_video_render_client


def setup_services():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    render_service = RenderService(job_repo=InMemoryRenderJobRepository())
    set_render_service(render_service)
    return media_service, timeline_service, render_service


def seed_project(duration_ms: int = 25000):
    media_service, timeline_service, render_service = setup_services()
    tmp_vid = Path(tempfile.mkdtemp()) / "stub.mp4"
    tmp_vid.write_bytes(b"video")
    asset = media_service.register_remote(MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_vid)))
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Chunk Demo"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=duration_ms,
            start_ms_on_timeline=0,
        )
    )
    return project, render_service


def test_chunk_plan_overlap_boundaries():
    project, _ = seed_project(duration_ms=25000)
    client = make_video_render_client()
    resp = client.post(
        "/video/render/chunks/plan",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "project_id": project.id,
            "render_profile": "social_1080p_h264",
            "segment_duration_ms": 10000,
            "overlap_ms": 500,
        },
    )
    assert resp.status_code == 200
    segments = resp.json()
    assert len(segments) == 3
    assert segments[0]["start_ms"] == 0
    assert segments[0]["overlap_ms"] == 500
    assert segments[-1]["end_ms"] == 25000


def test_segment_jobs_and_stitch_plan():
    project, render_service = seed_project(duration_ms=2000)
    # Avoid hitting ffmpeg during tests
    render_service._execute_plan = types.MethodType(
        lambda self, plan, *, stage="render timeline", hint=None: plan.output_path,
        render_service,
    )

    client = make_video_render_client()
    jobs_resp = client.post(
        "/video/render/jobs/chunked",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "project_id": project.id,
            "render_profile": "social_1080p_h264",
            "segment_duration_ms": 1000,
            "overlap_ms": 100,
        },
    )
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) == 2

    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev", "X-Project-Id": project.id}
    for job in jobs:
        run_resp = client.post(f"/video/render/jobs/{job['id']}/run", headers=headers)
        assert run_resp.status_code == 200
        assert run_resp.json()["status"] in {"succeeded", "failed"}

    stitch_resp = client.post(
        "/video/render/chunks/stitch",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "project_id": project.id,
            "render_profile": "social_1080p_h264",
            "segment_job_ids": [j["id"] for j in jobs],
            "normalize_audio": True,
        },
    )
    assert stitch_resp.status_code == 200
    stitched = stitch_resp.json()
    assert stitched["artifact_id"]
    assert stitched["plan_preview"]["steps"][0]["description"] == "stitch segments"
