from __future__ import annotations

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.maybes.service import MaybesService


def test_maybes_endpoints_crud(monkeypatch):
    import engines.maybes.routes as routes

    events = []
    svc = MaybesService(event_logger=lambda e: events.append(e))
    routes.service = svc

    client = TestClient(create_app())
    create_payload = {
        "tenant_id": "t_demo",
        "user_id": "user123",
        "body": "note body",
        "title": "title",
        "tags": ["alpha", "beta"],
        "origin_ref": {"surface": "app"},
    }
    resp = client.post("/api/maybes", json=create_payload)
    assert resp.status_code == 200
    note = resp.json()
    assert note["asset_type"] == "maybes_note"
    assert events and events[-1].event_type == "maybes_created"

    resp = client.get("/api/maybes", params={"tenant_id": "t_demo", "user_id": "user123", "tags": "alpha"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    maybes_id = items[0]["maybes_id"]

    resp = client.patch(
        f"/api/maybes/{maybes_id}",
        params={"tenant_id": "t_demo", "user_id": "user123"},
        json={"body": "updated text", "is_pinned": True},
    )
    assert resp.status_code == 200
    assert resp.json()["body"] == "updated text"

    resp = client.post(
        "/api/maybes/canvas-layout",
        json={
            "tenant_id": "t_demo",
            "user_id": "user123",
            "layouts": [
                {"maybes_id": maybes_id, "layout_x": 1.0, "layout_y": 2.0, "layout_scale": 0.5}
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["layouts"][0]["layout_scale"] == 0.5

    resp = client.delete(f"/api/maybes/{maybes_id}", params={"tenant_id": "t_demo", "user_id": "user123"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"
