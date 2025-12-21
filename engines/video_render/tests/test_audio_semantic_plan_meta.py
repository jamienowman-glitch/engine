import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.models import RenderRequest
from engines.video_render.routes import router as render_router
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service


def setup_env():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())
    return media_service, timeline_service


def test_render_plan_includes_audio_semantic_sources():
    media_service, timeline_service = setup_env()
    video_path = Path(tempfile.mkdtemp()) / "vid.mp4"
    video_path.write_bytes(b"video")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )
    # register audio semantic artifact
    semantic_path = Path(tempfile.mkdtemp()) / "semantic.json"
    semantic_path.write_text("{}", encoding="utf-8")
    media_service.register_artifact(
        ArtifactCreateRequest(
            tenant_id="t_test",
            env="dev",
            parent_asset_id=asset.id,
            kind="audio_semantic_timeline",  # type: ignore[arg-type]
            uri=str(semantic_path),
        )
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="AudioSem"))
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
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )

    app = FastAPI()
    app.include_router(render_router)
    client = TestClient(app)
    req = RenderRequest(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, render_profile="preview_720p_fast", dry_run=True)
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    meta = resp.json()["plan_preview"].get("meta", {})
    assert meta.get("audio_semantic_sources")
