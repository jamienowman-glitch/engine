import tempfile
from pathlib import Path

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.models import RenderRequest
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.tests.helpers import make_video_render_client


def _setup_services():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())
    return media_service, timeline_service


def _create_asset(media_service):
    tmp_file = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_file.write_bytes(b"123")
    return media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_file))
    )


def test_blend_mode_add_shows_blend_filter():
    media_service, timeline_service = _setup_services()
    asset_base = _create_asset(media_service)
    asset_overlay = _create_asset(media_service)

    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Blend Demo"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    track1 = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    track2 = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=1))
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track1.id,
            asset_id=asset_base.id,
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
            asset_id=asset_overlay.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
            blend_mode="add",
        )
    )

    client = make_video_render_client()
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="preview_720p_fast", dry_run=True)
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    filters = resp.json()["plan_preview"]["filters"]
    assert any("blend=all_mode=addition" in f for f in filters)


def test_speed_slow_mo_emits_setpts():
    media_service, timeline_service = _setup_services()
    asset = _create_asset(media_service)
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Speed Demo"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=2000,
            start_ms_on_timeline=0,
            speed=0.5,
        )
    )

    client = make_video_render_client()
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="preview_720p_fast", dry_run=True)
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    filters = resp.json()["plan_preview"]["filters"]
    assert any("setpts=PTS/0.5" in f for f in filters)
