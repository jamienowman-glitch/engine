"""Tests for Settings Engine."""
import os
from unittest import mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.cards.models import Card
from engines.nexus.index.models import SearchResult
from engines.nexus.settings.models import SettingsResponse
from engines.nexus.settings.service import SettingsService
from engines.nexus.settings.routes import router

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


def test_get_settings_facade_logic():
    """Verify SettingsService queries index and fetches cards."""
    mock_index = mock.MagicMock()
    mock_card_svc = mock.MagicMock()
    
    # Setup: Index returns an ID
    mock_index.search.return_value = [SearchResult(id="c1", score=1.0, metadata={})]
    # Setup: Card Service returns the Card
    mock_card = Card(
        card_id="c1", tenant_id="t1", env="dev", card_type="surface_settings", 
        version="v1", header={"foo": "bar"}, body_text="body", full_text="full"
    )
    mock_card_svc.get_card.return_value = mock_card
    
    service = SettingsService(index_service=mock_index, card_service=mock_card_svc)
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_user")
    
    # Test get_surface_settings
    result = service.get_surface_settings(ctx)
    
    assert result is not None
    assert result.card_id == "c1"
    
    # Verify Index Call filters
    mock_index.search.assert_called_once()
    query_arg = mock_index.search.call_args[0][1] # (ctx, query)
    assert query_arg.filters["card_type"] == "surface_settings"
    
    # Verify Card Fetch
    mock_card_svc.get_card.assert_called_with(ctx, "c1")


def test_routes_smoke():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    headers = {**_auth_headers(), "X-User-Id": "u_test"}
    
    # With defaults (Empty In-Memory Store), should return empty/null
    with mock.patch("engines.nexus.settings.service.default_event_logger"):
        with mock.patch(
            "engines.nexus.settings.service.SettingsService.get_surface_settings",
            return_value=SettingsResponse(items=[]),
        ):
            resp = client.get("/nexus/settings/surface", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"items": []}

        with mock.patch(
            "engines.nexus.settings.service.SettingsService.get_apps",
            return_value=SettingsResponse(items=[]),
        ):
            resp = client.get("/nexus/settings/apps", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"items": []}


def test_settings_require_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    resp = client.get("/nexus/settings/surface", headers=headers)
    assert resp.status_code == 401


def test_settings_reject_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = _auth_headers(tenant_id="t_beta", request_tenant="t_alpha")
    with mock.patch("engines.nexus.settings.service.default_event_logger"):
        resp = client.get("/nexus/settings/surface", headers=headers)
    assert resp.status_code == 403
