import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.canvas_artifacts.router import router as artifacts_router
from engines.identity.jwt_service import default_jwt_service

_client: TestClient | None = None


def _auth_token(tenant_id: str = "t_test", user_id: str = "u_test"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = "t_test", env: str = "dev"):
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id)}",
        "X-Tenant-Id": tenant_id,
        "X-Env": env,
    }


def setup_module(_module):
    os.environ.setdefault("AUTH_JWT_SIGNING", "canvas-secret")
    global _client
    app = FastAPI()
    app.include_router(artifacts_router)
    _client = TestClient(app)


def test_upload_artifact_success():
    client = _client
    headers = _auth_headers()
    files = {"file": ("test.png", b"fakeimage", "image/png")}
    resp = client.post("/canvas/c1/artifacts", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mime_type"] == "image/png"
    assert data["size"] == 9
    assert data["created_by"] == "u_test"
    assert data["key"].startswith("tenants/t_test/dev/canvas/")


def test_artifact_tenant_mismatch():
    client = _client
    headers = _auth_headers(tenant_id="t_bad")
    headers["X-Tenant-Id"] = "t_test"
    files = {"file": ("test.png", b"fakeimage", "image/png")}
    resp = client.post("/canvas/c1/artifacts", files=files, headers=headers)
    assert resp.status_code == 403


def test_missing_auth_rejected():
    client = _client
    files = {"file": ("test.png", b"fakeimage", "image/png")}
    resp = client.post(
        "/canvas/c1/artifacts",
        files=files,
        headers={"X-Tenant-Id": "t_test", "X-Env": "dev"},
    )
    assert resp.status_code == 401
