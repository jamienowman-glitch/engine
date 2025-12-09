from fastapi.testclient import TestClient

from engines.chat.service.server import create_app


def test_health() -> None:
    client = TestClient(create_app())
    resp = client.get("/chat/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_post_message_roundtrip() -> None:
    client = TestClient(create_app())
    payload = {
        "tenantId": "t_demo",
        "env": "dev",
        "surface": "web",
        "conversationId": "c1",
        "messageId": "m1",
        "message": "hello",
        "controls": {"temperatureBand": "cool"},
    }
    resp = client.post("/chat/web/c1", json=payload)
    assert resp.status_code == 200
    data = resp.json()["message"]
    assert data["response"].startswith("ack:")
    assert data["state"]["temperatureBand"] == "cool"
