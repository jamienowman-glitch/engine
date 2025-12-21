import json
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.audio_service.routes import router as audio_router


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository()))


class DummyCleanResult:
    def __init__(self, path: Path):
        self.cleaned_paths = [path]


class DummySegMeta:
    def __init__(self, path: Path):
        self.path = path
        self.start_seconds = 0.0
        self.end_seconds = 1.0


class DummySegResult:
    def __init__(self, path: Path):
        self.segments = [DummySegMeta(path)]


class DummyBeatMeta:
    def __init__(self):
        self.bpm = 120.0
        self.downbeats = [0.0]
        self.grid16 = 0.125

    def dict(self):
        return {"bpm": self.bpm, "downbeats": self.downbeats, "grid16": self.grid16}


class DummyBeatResult:
    def __init__(self, path: Path):
        self.features = {path: DummyBeatMeta()}


class DummyBars:
    def __init__(self):
        self.bars = [{"bar_index": 1, "text": "hi"}]

    def json(self, indent=2):
        return json.dumps({"bars": self.bars}, indent=indent)


class DummyVoiceResult:
    def __init__(self):
        self.artifact_id = "voice123"
        self.uri = "file:///tmp/voice.wav"
        self.meta = {"mode": "default"}


class DummyVoiceService:
    def enhance(self, req):
        return DummyVoiceResult()


def test_audio_service_endpoints(monkeypatch):
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)

    tmp_file = Path(tempfile.mkdtemp()) / "sample.wav"
    tmp_file.write_bytes(b"123")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="audio", source_uri=str(tmp_file))
    )

    # Patch audio engines to avoid ffmpeg deps
    import engines.audio_service.service as audio_service_module

    monkeypatch.setattr(audio_service_module, "clean_run", lambda cfg: DummyCleanResult(tmp_file))
    monkeypatch.setattr(audio_service_module, "segment_run", lambda cfg: DummySegResult(tmp_file))
    monkeypatch.setattr(audio_service_module, "beat_run", lambda cfg: DummyBeatResult(tmp_file))
    monkeypatch.setattr(audio_service_module.asr_backend, "transcribe_audio", lambda paths, **kwargs: [{"file": paths[0].name, "segments": []}])
    monkeypatch.setattr(audio_service_module, "align_run", lambda cfg: DummyBars())
    monkeypatch.setattr(audio_service_module, "get_voice_enhance_service", lambda: DummyVoiceService())

    app = FastAPI()
    app.include_router(audio_router)
    client = TestClient(app)

    # Preprocess
    resp = client.post("/audio/preprocess", json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id})
    assert resp.status_code == 200
    clean_artifacts = resp.json()
    assert clean_artifacts
    clean_artifact_id = clean_artifacts[0]["artifact_id"]

    # Segment
    resp = client.post(
        "/audio/segment",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "artifact_id": clean_artifact_id, "segment_seconds": 1},
    )
    assert resp.status_code == 200
    seg_artifacts = resp.json()
    assert seg_artifacts

    # Beat features
    resp = client.post(
        "/audio/beat-features",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "artifact_ids": [clean_artifact_id]},
    )
    assert resp.status_code == 200

    # ASR
    resp = client.post(
        "/audio/asr",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "artifact_ids": [clean_artifact_id]},
    )
    assert resp.status_code == 200
    asr_artifacts = resp.json()
    asr_id = asr_artifacts[0]["artifact_id"]

    # Align
    resp = client.post("/audio/align", json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asr_artifact_ids": [asr_id], "beat_meta": {}})
    assert resp.status_code == 200

    # Voice enhance passthrough
    resp = client.post(
        "/audio/voice-enhance",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "mode": "default", "aggressiveness": 0.4},
    )
    assert resp.status_code == 200
    assert resp.json()["artifact_id"] == "voice123"
