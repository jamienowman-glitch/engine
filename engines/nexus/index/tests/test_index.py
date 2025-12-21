"""Tests for Index Engine."""
import os
from unittest import mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.cards.models import Card
from engines.nexus.cards.service import CardService
from engines.nexus.index.service import CardIndexService
from engines.nexus.index.routes import router

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


SEARCH_PAYLOAD = {"query_text": "foo"}


def test_index_mock_embedding_deterministic():
    """Verify mock embedding produces same vector for same text."""
    service = CardIndexService()
    v1 = service._mock_embedding("hello world")
    v2 = service._mock_embedding("hello world")
    v3 = service._mock_embedding("different text")
    
    assert v1 == v2
    assert v1 != v3
    # Check normalization
    norm = sum(x*x for x in v1)
    assert abs(norm - 1.0) < 1e-6


def test_search_logic_in_memory():
    """Verify search recall and filtering."""
    service = CardIndexService()
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_user")
    
    # Manually seed store
    vec_match = service._mock_embedding("apple pie")
    vec_miss = service._mock_embedding("space ship")
    
    service.store.upsert("c1", vec_match, {"tenant_id": "t_test", "env": "dev", "card_type": "recipe"})
    service.store.upsert("c2", vec_miss, {"tenant_id": "t_test", "env": "dev", "card_type": "scifi"})
    # Document in other tenant (same text)
    service.store.upsert("c3", vec_match, {"tenant_id": "t_other", "env": "dev", "card_type": "recipe"})
    
    # Search for "apple" in t_test
    from engines.nexus.index.models import SearchQuery
    results = service.search(ctx, SearchQuery(query_text="apple pie", top_k=5))
    
    # Should find c1 (best match), maybe low score dependent on hash
    # Should NOT find c3 (wrong tenant)
    # Should NOT find c2 (low score, but if top_k is high it might appear if score > 0? Actually dot product might be low/neg)
    
    ids = [r.id for r in results]
    assert "c1" in ids
    assert "c3" not in ids
    
    # Verify Metadata filter
    results_filter = service.search(ctx, SearchQuery(query_text="apple pie", filters={"card_type": "scifi"}, top_k=5))
    ids_filter = [r.id for r in results_filter]
    assert "c2" in ids_filter
    assert "c1" not in ids_filter


def test_card_service_triggers_indexing():
    """Verify creating a card triggers the index service."""
    index_service = mock.MagicMock()
    card_service = CardService(index_service=index_service)
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_user")
    
    with mock.patch("engines.nexus.cards.service.default_event_logger"):
        card_service.create_card(ctx, "card_type: test\n---\nHello")
        
    assert index_service.index_card.call_count == 1
    call_args = index_service.index_card.call_args
    # call_args[0] = (ctx, card)
    assert call_args[0][1].body_text == "Hello"


def test_routes_smoke():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    headers = {**_auth_headers(), "X-User-Id": "u_test"}
    with mock.patch("engines.nexus.index.service.default_event_logger"):
        resp = client.post("/nexus/search", json=SEARCH_PAYLOAD, headers=headers)

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_routes_require_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    resp = client.post("/nexus/search", json=SEARCH_PAYLOAD, headers=headers)
    assert resp.status_code == 401


def test_routes_reject_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = _auth_headers(tenant_id="t_beta", request_tenant="t_alpha")
    with mock.patch("engines.nexus.index.service.default_event_logger"):
        resp = client.post("/nexus/search", json=SEARCH_PAYLOAD, headers=headers)
    assert resp.status_code == 403
