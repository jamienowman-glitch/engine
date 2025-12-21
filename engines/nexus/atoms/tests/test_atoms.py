"""Tests for Atoms Engine."""
import os
from unittest import mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.atoms.models import AtomArtifact
from engines.nexus.atoms.service import AtomService
from engines.nexus.atoms.routes import router

os.environ.setdefault("AUTH_JWT_SIGNING", "phase2-secret")


def _auth_token(tenant_id: str = "t_demo", user_id: str = "u_demo") -> str:
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = "t_demo", request_tenant: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id)}",
        "X-Tenant-Id": request_tenant or tenant_id,
        "X-Env": "dev",
    }


PAYLOAD = {"raw_asset_id": "r1", "op_type": "identity"}


def test_atom_creation_deterministic():
    """Verify atom creation logic and model default fields."""
    service = AtomService()
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_bot")
    
    # Mock event logger
    with mock.patch("engines.nexus.atoms.service.default_event_logger") as mock_log:
        atom = service.create_atom_from_raw(
            ctx, 
            raw_asset_id="raw123", 
            op_type="mock_text_split", 
            params={"text_chunk": "hello world"}
        )
    
    assert atom.tenant_id == "t_test"
    assert atom.parent_asset_id == "raw123"
    assert atom.op_type == "mock_text_split"
    assert atom.content == "hello world"
    assert atom.created_by == "u_bot"
    
    # Verify persistence
    saved = service.get_atom(ctx, atom.atom_id)
    assert saved.atom_id == atom.atom_id
    
    # Verify lineage log
    assert mock_log.call_count == 1
    entry = mock_log.call_args[0][0]
    assert entry.event_type == "atom_created"
    assert entry.origin_ref["parent_asset_id"] == "raw123"


def test_atom_routes_smoke():
    """Smoke test for atom routes."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    headers = {**_auth_headers(), "X-User-Id": "u_test"}

    # Mock event logger at the route level to avoid side effects
    with mock.patch("engines.nexus.atoms.service.default_event_logger"):
        resp = client.post("/nexus/atoms/create-from-raw", params=PAYLOAD, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["op_type"] == "identity"
    assert data["tenant_id"] == "t_demo"


def test_atom_routes_require_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    resp = client.post("/nexus/atoms/create-from-raw", params=PAYLOAD, headers=headers)
    assert resp.status_code == 401


def test_atom_routes_reject_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = _auth_headers(tenant_id="t_beta", request_tenant="t_alpha")
    with mock.patch("engines.nexus.atoms.service.default_event_logger"):
        resp = client.post("/nexus/atoms/create-from-raw", params=PAYLOAD, headers=headers)
    assert resp.status_code == 403
