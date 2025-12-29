import tempfile
from pathlib import Path

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.tests.helpers import make_video_render_client


def setup_services():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())
    return media_service, timeline_service


def test_loudnorm_in_plan():
    media_service, timeline_service = setup_services()
    tmp_file = Path(tempfile.mkdtemp()) / "audio.wav"
    tmp_file.write_bytes(b"123")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(tmp_file))
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Loud Demo"))
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
    resp = client.post(
        "/video/render/dry-run",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "project_id": project.id,
            "render_profile": "social_1080p_h264",
            "normalize_audio": True,
            "target_loudness_lufs": -14,
            "dry_run": True,
        },
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    assert any("loudnorm=I=-14" in f for f in plan["audio_filters"])
