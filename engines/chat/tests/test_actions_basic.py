from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.chat.service.routes_actions import router as actions_router
from engines.chat.tests.auth_helpers import auth_headers


def _actions_app():
    app = FastAPI()
    app.include_router(actions_router)
    return app


def test_strategy_lock_action_stub() -> None:
    client = TestClient(_actions_app())
    headers = auth_headers()
    payload = {
        "tenantId": "t_demo",
        "env": "dev",
        "surface": "web",
        "conversationId": "c1",
        "scope": "session",
        "confirm": False,
    }
    resp = client.post("/chat/actions/strategy_lock", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["action"] == "strategy_lock"


def test_three_wise_action_stub() -> None:
    client = TestClient(_actions_app())
    headers = auth_headers()
    payload = {
        "tenantId": "t_demo",
        "env": "dev",
        "surface": "web",
        "conversationId": "c1",
        "prompt": "check this",
    }
    resp = client.post("/chat/actions/three_wise", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["action"] == "three_wise"
