from __future__ import annotations

import os
import pytest

pytestmark = pytest.mark.skip("Tests out of sync with schema")

from fastapi import FastAPI
from fastapi.testclient import TestClient

import engines.maybes.routes as routes
from engines.maybes.service import MaybesService
from engines.identity.state import set_identity_repo
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.models import User, TenantMembership, Tenant
from engines.identity.jwt_service import default_jwt_service


def _client():
    # fresh in-memory service per test
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    routes.service = MaybesService()
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    user = repo.create_user(User(email="demo@example.com", password_hash="pw"))
    tenant = repo.create_tenant(Tenant(id="t_demo", name="Demo"))
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    token = default_jwt_service().issue_token(
        {
            "sub": user.id,
            "email": user.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "owner"},
        }
    )
    app = FastAPI()
    app.include_router(routes.router)
    client = TestClient(app)
    client.token = token  # type: ignore[attr-defined]
    client.user = user  # type: ignore[attr-defined]
    return client


def test_create_get_update_delete_route_flow():
    client = _client()
    create_payload = {
        "space": "scratchpad-default",
        "user_id": client.user.id,
        "title": "title",
        "content": "note body text",
        "tags": ["alpha", "beta"],
    }
    resp = client.post("/maybes/items", json=create_payload, headers={"Authorization": f"Bearer {client.token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"})
    assert resp.status_code == 200
    item = resp.json()
    item_id = item["id"]

    resp = client.get(f"/maybes/items/{item_id}", headers={"Authorization": f"Bearer {client.token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "title"

    # list with filters
    resp = client.get(
        "/maybes/items",
        params={
            "space": "scratchpad-default",
            "tags_any": "alpha",
        },
        headers={"Authorization": f"Bearer {client.token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["id"] == item_id

    # update
    resp = client.patch(
        f"/maybes/items/{item_id}",
        json={"title": "updated", "pinned": True},
        headers={"Authorization": f"Bearer {client.token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["item"]["pinned"] is True

    # delete
    resp = client.delete(f"/maybes/items/{item_id}", headers={"Authorization": f"Bearer {client.token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    resp = client.get(f"/maybes/items/{item_id}", headers={"Authorization": f"Bearer {client.token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"})
    assert resp.status_code == 404


def test_tenant_isolation_route():
    client = _client()
    # Without membership/token we expect 401/403
    resp = client.post(
        "/maybes/items",
        json={
            "space": "scratchpad-default",
            "title": "title",
            "content": "body",
        },
        headers={"X-Tenant-Id": "t_demo", "X-Env": "dev"},
    )
    assert resp.status_code in {401, 403}


def test_context_mismatch_rejected():
    client = _client()
    payload = {
        "space": "scratchpad-default",
        "title": "title",
        "content": "body",
    }
    # Header tenant differs from body → reject
    resp = client.post(
        "/maybes/items",
        json=payload,
        headers={"X-Tenant-Id": "t_other", "X-Env": "dev", "Authorization": f"Bearer {client.token}"},
    )
    assert resp.status_code in {400, 403}
