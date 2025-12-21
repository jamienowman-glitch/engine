"""Tests for Cards Engine."""
import os
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.cards.parser import parse_card_text
from engines.nexus.cards.service import CardService
from engines.nexus.cards.routes import router

os.environ.setdefault("AUTH_JWT_SIGNING", "phase2-secret")


def _card_client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _auth_token(tenant_id: str = "t_demo", user_id: str = "u_demo"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "owner"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = "t_demo", request_tenant: str | None = None):
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id)}",
        "X-Tenant-Id": request_tenant or tenant_id,
        "X-Env": "dev",
    }


def test_parser_valid():
    text = "card_type: kpi\nversion: v1\n---\nHello world"
    header, body = parse_card_text(text)
    assert header["card_type"] == "kpi"
    assert body == "Hello world"

def test_parser_frontmatter_style():
    text = "---\ncard_type: kpi\n---\nBody content"
    header, body = parse_card_text(text)
    assert header["card_type"] == "kpi"
    assert body == "Body content"

def test_parser_invalid_yaml():
    text = "invalid_yaml: [ unclosed\n---\nBody"
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        parse_card_text(text)

def test_parser_missing_separator():
    text = "Just some text without separator"
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        parse_card_text(text)

def test_card_creation_flow():
    service = CardService()
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_user")
    
    text = "card_type: persona\nversion: v1\n---\nI am a helper."
    
    with mock.patch("engines.nexus.cards.service.default_event_logger") as mock_log:
        card = service.create_card(ctx, text)
    
    assert card.card_type == "persona"
    assert card.body_text == "I am a helper."
    assert card.tenant_id == "t_test"
    
    # Verify persistence
    saved = service.get_card(ctx, card.card_id)
    assert saved.card_id == card.card_id

    # Verify event
    assert mock_log.call_count == 1
    entry = mock_log.call_args[0][0]
    assert entry.event_type == "card_created"

CARD_TEXT = "card_type: note\n---\nMy Note"


def test_routes_smoke():
    client = _card_client()
    headers = {**_auth_headers(), "Content-Type": "text/plain"}

    with mock.patch("engines.nexus.hardening.gate_chain.GateChain.run"):
        with mock.patch("engines.nexus.cards.service.default_event_logger"):
            resp = client.post("/nexus/cards", data=CARD_TEXT, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["card_type"] == "note"
    assert data["body_text"] == "My Note"


def test_cards_require_auth():
    client = _card_client()
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev", "Content-Type": "text/plain"}

    resp = client.post("/nexus/cards", data=CARD_TEXT, headers=headers)
    assert resp.status_code == 401


def test_cards_reject_cross_tenant():
    client = _card_client()
    headers = {**_auth_headers(tenant_id="t_beta", request_tenant="t_alpha"), "Content-Type": "text/plain"}

    resp = client.post("/nexus/cards", data=CARD_TEXT, headers=headers)
    assert resp.status_code == 403
