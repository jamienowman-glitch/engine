import tempfile
from pathlib import Path

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.audio_semantic_timeline.service import (
    AudioSemanticService,
    SPEED_CHANGE_LIMIT,
    StubAudioSemanticBackend,
    set_audio_semantic_service,
)
from engines.audio_semantic_timeline.models import AudioSemanticAnalyzeRequest, AudioSemanticTimelineSummary
from engines.audio_semantic_timeline.routes import router as semantic_router
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, get_timeline_service, set_timeline_service


class DummyStorage:
    def upload_file(self, file_path: Path, bucket: str, key: str) -> str:
        return f"gs://{bucket}/{key}"
    def get_signed_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        return f"https://storage.googleapis.com/{bucket}/{key}"
    def delete_file(self, bucket: str, key: str) -> None:
        pass


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository(), storage=DummyStorage()))
    set_audio_semantic_service(AudioSemanticService(backend=StubAudioSemanticBackend()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))


def _seed_clip(asset_id: str, speed: float = 1.0) -> Clip:
    timeline = get_timeline_service()
    project = timeline.create_project(
        VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="p1", description=None)
    )
    sequence = timeline.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="s1", duration_ms=60000)
    )
    track = timeline.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    return timeline.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset_id,
            artifact_id=None,
            in_ms=5000.0,
            out_ms=15000.0,
            start_ms_on_timeline=0.0,
            speed=speed,
        )
    )


def test_audio_semantic_analyze_and_get():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=DummyStorage())
    set_media_service(media_service)
    set_audio_semantic_service(AudioSemanticService(backend=StubAudioSemanticBackend()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))
    audio_path = Path(tempfile.mkdtemp()) / "audio.mp3"
    audio_path.write_bytes(b"dummy")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )

    app = FastAPI()
    app.include_router(semantic_router)
    client = TestClient(app)
    resp = client.post(
        "/audio/semantic-timeline/analyze",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "asset_id": asset.id,
            "include_beats": True,
            "include_speech_music": True,
        },
    )
    assert resp.status_code == 200
    artifact_id = resp.json()["audio_semantic_artifact_id"]
    artifact = media_service.get_artifact(artifact_id)
    assert artifact is not None
    assert artifact.kind == "audio_semantic_timeline"
    assert artifact.meta.get("semantic_version") is not None
    assert isinstance(artifact.meta.get("audio_semantic_cache_key"), str)
    assert artifact.meta["backend_type"] == "stub"
    result_meta = resp.json()["meta"]
    assert result_meta["cache_key"] == artifact.meta["audio_semantic_cache_key"]
    assert result_meta["cache_hit"] is False
    assert "backend_info" in result_meta

    resp_get = client.get(f"/audio/semantic-timeline/{artifact_id}")
    assert resp_get.status_code == 200
    summary = AudioSemanticTimelineSummary(**resp_get.json()["summary"])
    assert summary.events
    assert summary.beats
    assert summary.events == sorted(summary.events, key=lambda e: e.start_ms)


def test_audio_semantic_by_clip_slicing():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=DummyStorage())
    set_media_service(media_service)
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))
    set_audio_semantic_service(AudioSemanticService(backend=StubAudioSemanticBackend()))
    audio_path = Path(tempfile.mkdtemp()) / "audio2.mp3"
    audio_path.write_bytes(b"dummy2")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )
    clip = _seed_clip(asset.id, speed=1.25)

    app = FastAPI()
    app.include_router(semantic_router)
    client = TestClient(app)
    resp = client.post(
        "/audio/semantic-timeline/analyze",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id},
    )
    assert resp.status_code == 200

    resp_slice = client.get(f"/audio/semantic-timeline/by-clip/{clip.id}")
    assert resp_slice.status_code == 200
    resp_payload = resp_slice.json()
    sliced = AudioSemanticTimelineSummary(**resp_payload["summary"])
    assert all(0 <= ev.start_ms <= ev.end_ms <= (clip.out_ms - clip.in_ms) for ev in sliced.events)
    assert all(0 <= b.time_ms <= (clip.out_ms - clip.in_ms) for b in sliced.beats)
    assert resp_payload["summary"]["meta"]["clip_relative"] is True
    assert resp_payload["summary"]["meta"]["speed_change_limit"] == SPEED_CHANGE_LIMIT
    assert resp_payload["summary"]["meta"]["speed_change"] == clip.speed
    assert resp_payload["summary"]["meta"]["speed_change_limited"] is True


def test_audio_semantic_context_validation():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=DummyStorage())
    set_media_service(media_service)
    service = AudioSemanticService(backend=StubAudioSemanticBackend())
    set_audio_semantic_service(service)
    audio_path = Path(tempfile.mkdtemp()) / "audio_invalid.mp3"
    audio_path.write_bytes(b"dummy")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )
    req_invalid_tenant = AudioSemanticAnalyzeRequest(
        tenant_id="t_unknown",
        env="dev",
        user_id="u1",
        asset_id=asset.id,
    )
    with pytest.raises(ValueError):
        service.analyze(req_invalid_tenant)
    req_missing_env = AudioSemanticAnalyzeRequest(
        tenant_id="t_test",
        env="",
        user_id="u1",
        asset_id=asset.id,
    )
    with pytest.raises(ValueError):
        service.analyze(req_missing_env)


def test_missing_dependency_uses_stub(monkeypatch):
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=DummyStorage())
    set_media_service(media_service)
    monkeypatch.setattr("engines.audio_semantic_timeline.service._try_import", lambda name: None)
    service = AudioSemanticService()
    set_audio_semantic_service(service)
    audio_path = Path(tempfile.mkdtemp()) / "audio_stub.mp3"
    audio_path.write_bytes(b"dummy")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )
    req = AudioSemanticAnalyzeRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        asset_id=asset.id,
    )
    result = service.analyze(req)
    artifact = media_service.get_artifact(result.audio_semantic_artifact_id)
    assert artifact.meta["backend_type"] == "stub"
    assert artifact.meta["semantic_version"] == "audio_semantic_stub_v1"
    assert artifact.meta["backend"] == "audio_semantic_stub_v1"
    assert result.meta["backend_type"] == "stub"


def test_backend_selection_env(monkeypatch):
    monkeypatch.setenv("AUDIO_SEMANTIC_BACKEND", "stub")
    svc = AudioSemanticService()
    assert isinstance(svc.backend, StubAudioSemanticBackend)
    monkeypatch.delenv("AUDIO_SEMANTIC_BACKEND", raising=False)
