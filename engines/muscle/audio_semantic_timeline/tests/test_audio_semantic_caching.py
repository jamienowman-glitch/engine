import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.audio_semantic_timeline.models import AudioSemanticAnalyzeRequest
from engines.audio_semantic_timeline.routes import router as semantic_router
from engines.audio_semantic_timeline.service import AudioSemanticService, set_audio_semantic_service
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service


class CountingBackend:
    backend_version = "audio_semantic_stub_v1"

    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, audio_path, include_beats, include_speech_music, min_silence_ms, loudness_window_ms):
        self.calls += 1
        return AudioSemanticAnalyzeRequest  # type: ignore


class DummyStorage:
    def upload_file(self, file_path: Path, bucket: str, key: str) -> str:
        return f"gs://{bucket}/{key}"
    def get_signed_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        return f"https://storage.googleapis.com/{bucket}/{key}"
    def delete_file(self, bucket: str, key: str) -> None:
        pass

def test_audio_semantic_caching(monkeypatch):
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=DummyStorage())
    set_media_service(media_service)
    backend_calls = {"count": 0}

    class DummyBackend:
        backend_version = "audio_semantic_stub_v1"

        def analyze(self, audio_path, include_beats, include_speech_music, min_silence_ms, loudness_window_ms):
            backend_calls["count"] += 1
            from engines.audio_semantic_timeline.models import AudioSemanticTimelineSummary, AudioEvent

            return AudioSemanticTimelineSummary(
                asset_id="",
                duration_ms=10000,
                events=[AudioEvent(kind="speech", start_ms=0, end_ms=1000)],
                beats=[],
                meta={},
            )

    set_audio_semantic_service(AudioSemanticService(backend=DummyBackend()))

    audio_path = Path(tempfile.mkdtemp()) / "audio.wav"
    audio_path.write_bytes(b"dummy")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )

    app = FastAPI()
    app.include_router(semantic_router)
    client = TestClient(app)

    payload = {"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id}
    resp1 = client.post("/audio/semantic-timeline/analyze", json=payload)
    assert resp1.status_code == 200
    assert backend_calls["count"] == 1

    resp2 = client.post("/audio/semantic-timeline/analyze", json=payload)
    assert resp2.status_code == 200
    assert backend_calls["count"] == 1  # cache hit

    resp3 = client.post("/audio/semantic-timeline/analyze", json={**payload, "include_beats": False})
    assert resp3.status_code == 200
    assert backend_calls["count"] == 2

    initial_key = resp1.json()["meta"]["cache_key"]
    assert "u1" in initial_key
    assert resp2.json()["meta"]["cache_key"] == initial_key
    assert resp3.json()["meta"]["cache_key"] != initial_key
