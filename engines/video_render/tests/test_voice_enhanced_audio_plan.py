import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.models import RenderRequest
from engines.video_render.service import RenderService, set_render_service
from engines.video_render.routes import router as render_router
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service


def setup_env():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())
    return media_service, timeline_service


def create_project_with_clip(media_service, timeline_service, has_voice_artifact: bool, track_role: str = "dialogue"):
    video_path = Path(tempfile.mkdtemp()) / "vid.mp4"
    video_path.write_bytes(b"video")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )
    if has_voice_artifact:
        voice_path = Path(tempfile.mkdtemp()) / "voice_enh.wav"
        voice_path.write_bytes(b"audio")
        media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id="t_test",
                env="dev",
                parent_asset_id=asset.id,
                kind="audio_voice_enhanced",  # type: ignore[arg-type]
                uri=str(voice_path),
                meta={"mode": "default"},
            )
        )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="VoicePlan"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    track = timeline_service.create_track(
        Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0, audio_role=track_role)
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
    return project


def test_render_prefers_voice_enhanced_when_available():
    media_service, timeline_service = setup_env()
    project = create_project_with_clip(media_service, timeline_service, has_voice_artifact=True)

    app = FastAPI()
    app.include_router(render_router)
    client = TestClient(app)
    req = RenderRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        project_id=project.id,
        render_profile="preview_720p_fast",
        dry_run=True,
        use_voice_enhanced_audio=True,
    )
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    inputs = resp.json()["plan_preview"]["inputs"]
    assert any("voice_enh" in inp for inp in inputs)


def test_render_voice_enhance_missing_warning():
    media_service, timeline_service = setup_env()
    project = create_project_with_clip(media_service, timeline_service, has_voice_artifact=False)
    app = FastAPI()
    app.include_router(render_router)
    client = TestClient(app)
    req = RenderRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        project_id=project.id,
        render_profile="preview_720p_fast",
        dry_run=True,
        use_voice_enhanced_audio=True,
        voice_enhance_if_available_only=False,
    )
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    meta = resp.json()["plan_preview"].get("meta", {})
    assert meta.get("voice_enhance_warnings")


def test_audio_stream_selection_dialogue_vs_music():
    media_service, timeline_service = setup_env()
    video_path = Path(tempfile.mkdtemp()) / "vid.mp4"
    video_path.write_bytes(b"video")
    asset_dialog = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )
    voice_path = Path(tempfile.mkdtemp()) / "voice_enh.wav"
    voice_path.write_bytes(b"audio")
    media_service.register_artifact(
        ArtifactCreateRequest(
            tenant_id="t_test",
            env="dev",
            parent_asset_id=asset_dialog.id,
            kind="audio_voice_enhanced",  # type: ignore[arg-type]
            uri=str(voice_path),
            meta={"mode": "default"},
        )
    )
    music_asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(video_path))
    )

    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Roles"))
    sequence = timeline_service.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30)
    )
    dialog_track = timeline_service.create_track(
        Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0, audio_role="dialogue")
    )
    music_track = timeline_service.create_track(
        Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="audio", order=1, audio_role="music")
    )
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=dialog_track.id,
            asset_id=asset_dialog.id,
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
            track_id=music_track.id,
            asset_id=music_asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )

    app = FastAPI()
    app.include_router(render_router)
    client = TestClient(app)
    req = RenderRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        project_id=project.id,
        render_profile="preview_720p_fast",
        dry_run=True,
        use_voice_enhanced_audio=True,
    )
    resp = client.post("/video/render/dry-run", json=req.model_dump())
    assert resp.status_code == 200
    meta = resp.json()["plan_preview"].get("meta", {})
    selections = meta.get("audio_voice_enhance_selection", [])
    assert any(sel["role"] == "dialogue" and sel["source"] == "enhanced" for sel in selections)
    assert any(sel["role"] == "music" and sel["source"] == "original" for sel in selections)
