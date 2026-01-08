from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from engines.chat.service.http_transport import register_error_handlers
from engines.common.error_envelope import error_response, missing_route_error


def _build_test_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    return app


def test_http_exception_returns_canonical_envelope():
    app = _build_test_app()

    @app.get("/test-error")
    def _raise_error() -> None:
        raise error_response(
            code="test_error",
            message="Test message",
            status_code=403,
            gate="firearms",
            action_name="dangerous_action",
            details={"current": 100, "limit": 50},
        )

    client = TestClient(app)
    response = client.get("/test-error")

    assert response.status_code == 403
    payload = response.json()
    assert "error" in payload

    error = payload["error"]
    assert error["code"] == "test_error"
    assert error["message"] == "Test message"
    assert error["http_status"] == 403
    assert error["gate"] == "firearms"
    assert error["action_name"] == "dangerous_action"
    assert error["details"] == {"current": 100, "limit": 50}


def test_validation_error_returns_details_and_status():
    app = _build_test_app()

    class InputModel(BaseModel):
        value: int

    @app.post("/validate")
    def _validate(payload: InputModel) -> dict:
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/validate", json={"value": "nope"})

    assert response.status_code == 400
    payload = response.json()
    error = payload["error"]
    assert error["code"] == "validation.error"
    assert error["http_status"] == 400
    assert isinstance(error["details"], dict)
    assert "errors" in error["details"]
    assert isinstance(error["details"]["errors"], list)


def test_missing_route_envelope_preserves_code_and_status():
    app = _build_test_app()

    @app.get("/missing")
    def _raise_missing() -> None:
        raise missing_route_error("canvas_store", "tenant-1", "dev")

    client = TestClient(app)
    response = client.get("/missing")

    assert response.status_code == 503
    payload = response.json()
    error = payload["error"]
    assert error["code"] == "canvas_store.missing_route"
    assert error["http_status"] == 503
