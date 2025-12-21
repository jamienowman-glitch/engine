"""Tests for Influence Packs Engine."""
import os
from unittest import mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.index.models import SearchResult, SearchQuery
from engines.nexus.packs.service import PackService
from engines.nexus.packs.routes import router

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


PACK_REQUEST = {"query": {"query_text": "foo"}}


def test_create_pack_passthrough():
    """Verify pack creation wraps index results without modification."""
    mock_index = mock.MagicMock()
    # Mock index returns one result with a snippet
    mock_index.search.return_value = [
        SearchResult(id="c1", score=0.9, metadata={}, snippet="Opaque Snippet")
    ]
    
    service = PackService(index_service=mock_index)
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_user")
    
    # Mock logger
    with mock.patch("engines.nexus.packs.service.default_event_logger") as mock_log:
        pack = service.create_pack(ctx, SearchQuery(query_text="foo"))
    
    # Verify Pack structure
    assert pack.tenant_id == "t_test"
    assert len(pack.card_refs) == 1
    
    # Verify Content Passthrough
    ref = pack.card_refs[0]
    assert ref.card_id == "c1"
    assert ref.score == 0.9
    assert ref.excerpt == "Opaque Snippet"
    
    # Verify Event Log
    assert mock_log.call_count == 1
    entry = mock_log.call_args[0][0]
    assert entry.event_type == "pack_created"
    assert entry.asset_id == pack.pack_id


def test_routes_smoke():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {**_auth_headers(), "X-User-Id": "u_test"}
    
    # Functional smoke test (will rely on real In-Memory index implicitly if we don't mock get_service)
    # The default PackService creates a NEW CardIndexService, which creates a NEW GLOBAL_STORE ref 
    # (since _GLOBAL_STORE is module level in index/service.py).
    # So searching "foo" in a fresh index returns empty list.
    
    with mock.patch("engines.nexus.packs.service.default_event_logger"):
        resp = client.post("/nexus/influence-pack", json=PACK_REQUEST, headers=headers)
        
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "t_demo"
    assert data["card_refs"] == [] # Empty results default


def test_routes_require_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    resp = client.post("/nexus/influence-pack", json=PACK_REQUEST, headers=headers)
    assert resp.status_code == 401


def test_routes_reject_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = _auth_headers(tenant_id="t_beta", request_tenant="t_alpha")
    with mock.patch("engines.nexus.packs.service.default_event_logger"):
        resp = client.post("/nexus/influence-pack", json=PACK_REQUEST, headers=headers)
    assert resp.status_code == 403
