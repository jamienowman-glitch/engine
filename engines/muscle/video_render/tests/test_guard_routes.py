from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from engines.video_render.routes import router, get_auth_context
from engines.identity.jwt_service import AuthContext


def _auth_context_for_tenant(tenant_id: str) -> AuthContext:
    return AuthContext(
        user_id="render_guard",
        email="render_guard@example.com",
        tenant_ids=[tenant_id],
        default_tenant_id=tenant_id,
        role_map={tenant_id: "owner"},
    )


def _build_app(auth_override=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if auth_override:
        app.dependency_overrides[get_auth_context] = auth_override
    return app


def test_missing_project_id_returns_400():
    app = _build_app(lambda: _auth_context_for_tenant("t_test"))
    client = TestClient(app)

    resp = client.get(
        "/video/render/jobs",
        headers={"X-Tenant-Id": "t_test", "X-Env": "dev"},
        params={"tenant_id": "t_test"},
    )
    assert resp.status_code == 400
    assert "project_id" in resp.json().get("detail", "")


def test_missing_auth_returns_401():
    app = _build_app()

    def _missing_auth_context():
        raise HTTPException(status_code=401, detail="missing bearer token")

    app.dependency_overrides[get_auth_context] = _missing_auth_context
    client = TestClient(app)

    resp = client.get(
        "/video/render/jobs",
        headers={"X-Tenant-Id": "t_test", "X-Env": "dev", "X-Project-Id": "p_render"},
        params={"tenant_id": "t_test"},
    )
    assert resp.status_code == 401


def test_tenant_membership_required_returns_403():
    app = _build_app(lambda: _auth_context_for_tenant("t_other"))
    client = TestClient(app)

    resp = client.get(
        "/video/render/jobs",
        headers={"X-Tenant-Id": "t_test", "X-Env": "dev", "X-Project-Id": "p_render"},
        params={"tenant_id": "t_test"},
    )
    assert resp.status_code == 403
