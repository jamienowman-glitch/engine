import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.audio_voice_enhance.models import VoiceEnhanceRequest
from engines.audio_voice_enhance.routes import router as voice_router
from engines.audio_voice_enhance.service import VoiceEnhanceService, set_voice_enhance_service
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service


class CountingBackend:
    backend_version = "test_backend_v1"

    def __init__(self) -> None:
        self.calls = 0

    def run(self, audio_path, mode, aggressiveness, preserve_ambience):
        self.calls += 1
        out = Path(tempfile.mkdtemp()) / f"{audio_path.stem}_enh.wav"
        out.write_bytes(b"voice")
        return out


def test_voice_enhance_caching_reuses_artifact():
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    backend = CountingBackend()
    set_voice_enhance_service(VoiceEnhanceService(backend=backend))

    audio_path = Path(tempfile.mkdtemp()) / "sample.wav"
    audio_path.write_bytes(b"dummy")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )

    app = FastAPI()
    app.include_router(voice_router)
    client = TestClient(app)

    req_payload = {"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "mode": "default", "aggressiveness": 0.5}
    resp1 = client.post("/audio/voice-enhance", json=req_payload)
    assert resp1.status_code == 200
    assert backend.calls == 1

    resp2 = client.post("/audio/voice-enhance", json=req_payload)
    assert resp2.status_code == 200
    assert backend.calls == 1  # cache hit

    resp3 = client.post("/audio/voice-enhance", json={**req_payload, "mode": "podcast"})
    assert resp3.status_code == 200
    assert backend.calls == 2  # new cache key
