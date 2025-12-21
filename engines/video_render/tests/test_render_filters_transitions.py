import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_timeline.models import Clip, Filter, FilterStack, Sequence, Track, Transition, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.service import set_render_service, RenderService


def test_filters_and_transitions_in_plan():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    vid = Path(tempfile.mkdtemp()) / "v.mp4"
    vid.write_bytes(b"video")
    asset = media_service.register_remote(MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(vid)))

    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Filters"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    clip1 = timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=0))
    clip2 = timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=1000))
    # Filter stack on clip1
    timeline_service.create_filter_stack(
        FilterStack(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            target_type="clip",
            target_id=clip1.id,
            filters=[Filter(type="exposure", params={"stops": 0.5}, enabled=True)],
        )
    )
    # Transition between clips
    timeline_service.create_transition(
        Transition(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            sequence_id=sequence.id,
            type="crossfade",
            duration_ms=500,
            from_clip_id=clip1.id,
            to_clip_id=clip2.id,
        )
    )

    client = TestClient(create_app())
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    assert any("eq=" in f for f in plan["filters"])
    assert any("xfade" in f for f in plan["filters"])
    transitions = plan["meta"]["transitions"]
    assert transitions
    first = transitions[0]
    assert first["type"] == "crossfade"
    assert first["order"] == 0
    assert first["duration_ms"] > 0
    assert plan["meta"]["render_profile"] == "social_1080p_h264"
    assert plan["meta"]["render_profile_description"] == "1080p H.264 for social delivery with balanced quality"
    assert first["video_alias"] == "fade"
    assert first["audio_alias"] == "acrossfade"
