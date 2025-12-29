import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.audio_voice_enhance.service import FfmpegVoiceEnhanceBackend, VoiceEnhanceService, set_voice_enhance_service
from engines.audio_voice_enhance.models import VoiceEnhanceRequest
from engines.audio_voice_enhance.routes import router as voice_router
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository()))
    set_voice_enhance_service(VoiceEnhanceService(backend=FfmpegVoiceEnhanceBackend()))


def test_voice_enhance_registers_artifact():
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    set_voice_enhance_service(VoiceEnhanceService(backend=FfmpegVoiceEnhanceBackend()))

    audio_path = Path(tempfile.mkdtemp()) / "sample.wav"
    audio_path.write_bytes(b"dummy")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(audio_path))
    )

    app = FastAPI()
    app.include_router(voice_router)
    client = TestClient(app)
    req = VoiceEnhanceRequest(tenant_id="t_test", env="dev", user_id="u1", asset_id=asset.id, mode="podcast", aggressiveness=0.7)
    resp = client.post("/audio/voice-enhance", json=req.model_dump())
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact_id"]
    art = media_service.get_artifact(body["artifact_id"])
    assert art is not None
    assert art.kind == "audio_voice_enhanced"

    resp_get = client.get(f"/audio/voice-enhance/{body['artifact_id']}")
    assert resp_get.status_code == 200
