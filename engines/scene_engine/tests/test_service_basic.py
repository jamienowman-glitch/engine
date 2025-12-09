from fastapi.testclient import TestClient

from engines.scene_engine.service.server import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_scene_build_roundtrip() -> None:
    client = TestClient(create_app())
    payload = {
        "grid": {"cols": 24, "rows": 1, "col_width": 1.0, "row_height": 1.0},
        "boxes": [
            {"id": "box1", "x": 0, "y": 0, "w": 4, "h": 3, "kind": "card"},
            {"id": "box2", "x": 5, "y": 0, "z": 1, "w": 2, "h": 2, "d": 1, "kind": "card"},
        ],
        "recipe": "wall",
    }
    resp = client.post("/scene/build", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "scene" in data
    assert len(data["scene"]["nodes"]) == 2
    assert data["scene"]["nodes"][0]["gridBox3D"]["w"] == 4
