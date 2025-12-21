from pathlib import Path
import importlib.util
import types

from fastapi.testclient import TestClient


def _load_server() -> types.ModuleType:
    server_path = Path(__file__).resolve().parents[1] / "service" / "server.py"
    spec = importlib.util.spec_from_file_location("bbk_server", server_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_health() -> None:
    server = _load_server()
    client = TestClient(server.create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "bbk"


def test_upload_and_process(tmp_path: Path, monkeypatch) -> None:
    server = _load_server()
    client = TestClient(server.create_app())
    # Stub audio_core runner to avoid heavy deps
    import importlib.util
    routes_path = Path(__file__).resolve().parents[1] / "service" / "routes.py"
    spec = importlib.util.spec_from_file_location("bbk_routes", routes_path)
    routes = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(routes)  # type: ignore[attr-defined]
    monkeypatch.setattr(routes.audio_core_runner, "run_pipeline", lambda raw_dir, work_dir, lora_config=None: {"asr": []})

    files = {"file": ("a.mp3", b"audio", "audio/mpeg")}
    resp = client.post("/bbk/upload-and-process", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "runId" in data
    assert data["status"] == "accepted"


def test_start_training_no_dataset() -> None:
    server = _load_server()
    client = TestClient(server.create_app())
    resp = client.post("/bbk/start-training")
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"
