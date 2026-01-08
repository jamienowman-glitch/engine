from __future__ import annotations

import base64
from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.chat.service.http_transport import register_error_handlers
from engines.common.identity import RequestContext
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext, default_jwt_service
from engines.identity.models import App, Surface
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.registry.routes import router, _resolve_auth_context
from engines.registry.service import (
    ComponentRegistryService,
    set_component_registry_service,
)


def _mock_auth_context() -> AuthContext:
    return AuthContext(
        user_id="test-user",
        email="test@example.com",
        tenant_ids=["t_registry"],
        default_tenant_id="t_registry",
        role_map={"t_registry": "owner"},
        provider="test",
        claims={},
    )


def _builder_atom_spec(id_suffix: str = "button", version: int = 1) -> Dict[str, Any]:
    return {
        "id": f"builder.{id_suffix}",
        "kind": "atom",
        "version": version,
        "schema": {"type": "object", "properties": {"label": {"type": "string"}}},
        "defaults": {"label": f"Click {id_suffix}"},
        "controls": {"fields": [{"name": "label", "type": "text"}]},
        "token_surface": ["/canvas/op/label"],
        "metadata": {"capabilities": {"read": True}},
    }


def _graphlens_spec(id_suffix: str = "scopes", version: int = 1) -> Dict[str, Any]:
    return {
        "id": f"graphlens.{id_suffix}",
        "kind": "lens",
        "version": version,
        "schema": {"type": "object", "properties": {"nodes": {"type": "array"}}},
        "defaults": {"nodes": []},
        "controls": {"mode": "graph"},
        "token_surface": [],
        "metadata": {"capabilities": {"graph": True}},
    }


@pytest.fixture(autouse=True)
def identity_repo_setup():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    repo.create_surface(Surface(tenant_id="t_registry", name="surface-registry"))
    repo.create_app(App(tenant_id="t_registry", name="app-registry"))
    return repo


@pytest.fixture
def context() -> RequestContext:
    ctx = RequestContext(
        tenant_id="t_registry",
        env="dev",
        mode="saas",
        project_id="proj",
        request_id="req-specs",
        user_id="user1",
    )
    ctx.surface_id = "surface-registry"
    return ctx


@pytest.fixture
def auth_token(monkeypatch) -> str:
    monkeypatch.setenv("AUTH_JWT_SIGNING", "test-specs-secret")
    def _raise_secret(self, tenant_id, env, slot):
        raise RuntimeError("no secret")
    monkeypatch.setattr(
        "engines.identity.jwt_service.TenantKeySelector.get_config",
        _raise_secret,
    )
    token = default_jwt_service().issue_token(
        {
            "sub": "test-user",
            "tenant_ids": ["t_registry"],
            "default_tenant_id": "t_registry",
            "role_map": {"t_registry": "owner"},
        }
    )
    return token


@pytest.fixture
def registry_headers(auth_token: str) -> Dict[str, str]:
    return {
        "X-Tenant-Id": "t_registry",
        "X-Mode": "saas",
        "X-Project-Id": "proj",
        "X-Surface-Id": "surface-registry",
        "X-App-Id": "app-registry",
        "Authorization": f"Bearer {auth_token}",
    }


@pytest.fixture
def fake_tabular(monkeypatch):
    class FakeTabularStoreService:
        _store: Dict[str, Dict[str, Dict[str, Any]]] = {}

        def __init__(self, context, resource_kind="component_registry"):
            self.context = context
            self.resource_kind = resource_kind

        def upsert(self, table_name: str, key: str, data: Dict[str, Any], context):
            table = FakeTabularStoreService._store.setdefault(table_name, {})
            table[key] = data

        def get(self, table_name: str, key: str, context):
            return FakeTabularStoreService._store.get(table_name, {}).get(key)

        def list_by_prefix(self, table_name: str, prefix: str, context):
            table = FakeTabularStoreService._store.get(table_name, {})
            return [
                value
                for stored_key, value in table.items()
                if stored_key.startswith(prefix)
            ]

    FakeTabularStoreService._store = {}
    monkeypatch.setattr(
        "engines.registry.repository.TabularStoreService",
        FakeTabularStoreService,
    )
    return FakeTabularStoreService


@pytest.fixture
def registry_service(fake_tabular) -> ComponentRegistryService:
    service = ComponentRegistryService()
    set_component_registry_service(service)
    return service


@pytest.fixture
def registry_app(registry_service: ComponentRegistryService) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[_resolve_auth_context] = lambda: _mock_auth_context()
    app.include_router(router)
    return app


@pytest.fixture
def registry_client(registry_app: FastAPI) -> TestClient:
    return TestClient(registry_app)


def _decode_cursor(cursor: str) -> int:
    padded = cursor + "=" * (-len(cursor) % 4)
    return int(base64.urlsafe_b64decode(padded).decode("ascii"))


def test_registry_specs_returns_builder_atom(context, registry_client, registry_headers, registry_service):
    registry_service.save_spec(context, _builder_atom_spec(version=5))
    response = registry_client.get(
        "/registry/specs", params={"kind": "atom"}, headers=registry_headers
    )
    assert response.status_code == 200
    payload = response.json()
    spec = payload["specs"][0]
    assert spec["controls"]["fields"][0]["name"] == "label"
    assert spec["token_surface"] == ["/canvas/op/label"]
    assert payload["version"] == 5
    assert payload["next_cursor"] is None


def test_registry_specs_returns_graphlens(context, registry_client, registry_headers, registry_service):
    registry_service.save_spec(context, _graphlens_spec(version=2))
    response = registry_client.get(
        "/registry/specs", params={"kind": "lens"}, headers=registry_headers
    )
    assert response.status_code == 200
    payload = response.json()
    spec = payload["specs"][0]
    assert spec["controls"]["mode"] == "graph"
    assert payload["version"] == 2


def test_registry_specs_pagination_and_cursor(context, registry_client, registry_headers, registry_service):
    registry_service.SPEC_PAGE_SIZE = 1
    registry_service.save_spec(context, _builder_atom_spec("alpha", version=1))
    registry_service.save_spec(context, _builder_atom_spec("beta", version=2))

    first = registry_client.get(
        "/registry/specs", params={"kind": "atom"}, headers=registry_headers
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["specs"][0]["id"] == "builder.alpha"
    assert first_payload["version"] == 2
    cursor = first_payload["next_cursor"]
    assert cursor is not None
    assert _decode_cursor(cursor) == 1

    second = registry_client.get(
        "/registry/specs",
        params={"kind": "atom", "cursor": cursor},
        headers=registry_headers,
    )
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["specs"][0]["id"] == "builder.beta"
    assert second_payload["next_cursor"] is None


def test_registry_specs_invalid_cursor_returns_envelope(registry_client, registry_headers):
    response = registry_client.get(
        "/registry/specs", params={"kind": "atom", "cursor": "not-a-cursor"}, headers=registry_headers
    )
    assert response.status_code == 410
    payload = response.json()
    assert payload["error"]["code"] == "component_registry.cursor_invalid"
    assert payload["error"]["http_status"] == 410


def test_registry_specs_missing_route(monkeypatch, registry_headers):
    class MissingTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no route")

    monkeypatch.setattr(
        "engines.registry.repository.TabularStoreService",
        MissingTabular,
    )
    service = ComponentRegistryService()
    set_component_registry_service(service)

    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[_resolve_auth_context] = lambda: _mock_auth_context()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/registry/specs", params={"kind": "atom"}, headers=registry_headers)
    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "component_registry.missing_route"
    assert payload["error"]["http_status"] == 503


def test_registry_specs_etag_caching(context, registry_client, registry_headers, registry_service):
    registry_service.save_spec(context, _builder_atom_spec(version=4))
    response = registry_client.get(
        "/registry/specs", params={"kind": "atom"}, headers=registry_headers
    )
    assert response.status_code == 200
    etag = response.headers.get("etag")
    assert etag

    cached = registry_client.get(
        "/registry/specs",
        params={"kind": "atom"},
        headers={**registry_headers, "If-None-Match": etag},
    )
    assert cached.status_code == 304
    assert cached.headers.get("etag") == etag


def test_registry_spec_detail_etag_and_not_found(context, registry_client, registry_headers, registry_service):
    spec_data = _builder_atom_spec(version=6)
    registry_service.save_spec(context, spec_data)
    response = registry_client.get(
        f"/registry/specs/{spec_data['id']}", headers=registry_headers
    )
    assert response.status_code == 200
    etag = response.headers.get("etag")
    assert etag

    cached = registry_client.get(
        f"/registry/specs/{spec_data['id']}",
        headers={**registry_headers, "If-None-Match": etag},
    )
    assert cached.status_code == 304
    assert cached.headers.get("etag") == etag

    missing = registry_client.get("/registry/specs/unknown", headers=registry_headers)
    assert missing.status_code == 404
    payload = missing.json()
    assert payload["error"]["code"] == "component_registry.spec_not_found"
    assert payload["error"]["details"]["spec_id"] == "unknown"


def test_registry_specs_restart_persistence(context, registry_service):
    registry_service.save_spec(context, _builder_atom_spec(version=7))
    reloaded = ComponentRegistryService()
    payload = reloaded.list_specs(context, kind="atom")
    assert payload.specs
    assert payload.specs[0].id == "builder.button"
    assert payload.version == 7
