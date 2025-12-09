from fastapi.testclient import TestClient

from engines.chat.service.server import create_app


def test_strategy_lock_action_stub() -> None:
    client = TestClient(create_app())
    payload = {
        "tenantId": "t_demo",
        "env": "dev",
        "surface": "web",
        "conversationId": "c1",
        "scope": "session",
        "confirm": False,
    }
    resp = client.post("/chat/actions/strategy_lock", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["action"] == "strategy_lock"


def test_three_wise_action_stub() -> None:
    client = TestClient(create_app())
    payload = {
        "tenantId": "t_demo",
        "env": "dev",
        "surface": "web",
        "conversationId": "c1",
        "prompt": "check this",
    }
    resp = client.post("/chat/actions/three_wise", json=payload)
    assert resp.status_code == 200
    assert resp.json()["action"] == "three_wise"
