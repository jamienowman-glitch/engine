import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.models import RenderRequest
from engines.video_render.service import set_render_service, RenderService
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))


def test_render_dry_run_minimal():
    media_service = MediaService(repo=InMemoryMediaRepository())
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

    client = TestClient(create_app())
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="social_1080p_h264", dry_run=True)
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"]
    assert body["plan_preview"]["output_path"]
    plan_meta = body["plan_preview"]["meta"]
    assert plan_meta["render_profile"] == "social_1080p_h264"
    assert "hardware_encoder" in plan_meta
    assert plan_meta["source_assets"] == [asset.id]
