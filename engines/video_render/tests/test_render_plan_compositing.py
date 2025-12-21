import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.service import set_render_service, RenderService


def test_render_plan_contains_overlay_and_profile():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    tmp_file = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_file.write_bytes(b"123")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_file))
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Overlay Demo"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track1 = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    track2 = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=1))
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track1.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track2.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )

    client = TestClient(create_app())
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    # Expect overlay filter present for two tracks
    assert any("overlay" in f for f in plan.get("filters", []))
    # Profile should reflect social_1080p_h264
    assert plan["profile"] == "social_1080p_h264"
