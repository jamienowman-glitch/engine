from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.video_360.routes import router
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext


def _auth_context_for_tenant(tenant_id: str) -> AuthContext:
    return AuthContext(
        user_id="guard360",
        email="guard360@example.com",
        tenant_ids=[tenant_id],
        default_tenant_id=tenant_id,
        role_map={tenant_id: "owner"},
    )


def _build_app(auth_override=None):
    app = FastAPI()
    app.include_router(router)
    if auth_override:
        app.dependency_overrides[get_auth_context] = auth_override
    return app


def test_missing_project_id_returns_400():
    app = _build_app(lambda: _auth_context_for_tenant("t1"))
    client = TestClient(app)
    resp = client.post(
        "/video/360/render",
        headers={"X-Tenant-Id": "t1", "X-Env": "dev"},  # project_id missing
        json={"tenant_id": "t1", "env": "dev", "asset_id": "a1"},
    )
    assert resp.status_code == 400
    assert "project_id" in resp.json().get("detail", "")


def test_missing_auth_returns_401():
    app = _build_app()
    client = TestClient(app)
    resp = client.post(
        "/video/360/render",
        headers={"X-Tenant-Id": "t_test", "X-Env": "dev", "X-Project-Id": "p360"},
        json={"tenant_id": "t_test", "env": "dev", "asset_id": "a1"},
    )
    assert resp.status_code == 401


def test_tenant_membership_required_returns_403():
    app = _build_app(lambda: _auth_context_for_tenant("other"))
    client = TestClient(app)
    resp = client.post(
        "/video/360/render",
        headers={"X-Tenant-Id": "t_test", "X-Env": "dev", "X-Project-Id": "p360"},
        json={"tenant_id": "t_test", "env": "dev", "asset_id": "a1"},
    )
    assert resp.status_code == 403
