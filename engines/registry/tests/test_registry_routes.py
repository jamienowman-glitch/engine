from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.chat.service.http_transport import register_error_handlers
from engines.common.identity import RequestContext
from engines.identity.jwt_service import AuthContext
from engines.registry.routes import router
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


@pytest.fixture
def context() -> RequestContext:
    ctx = RequestContext(
        tenant_id="t_registry",
        env="dev",
        mode="saas",
        project_id="proj",
        request_id="req-1",
        user_id="user1",
    )
    ctx.surface_id = "surface-registry"
    return ctx


@pytest.fixture
def registry_headers() -> Dict[str, str]:
    return {
        "X-Tenant-Id": "t_registry",
        "X-Mode": "saas",
        "X-Project-Id": "proj",
        "X-Surface-Id": "surface-registry",
        "Authorization": "Bearer fake-token",
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
    app.include_router(router)
    return app


@pytest.fixture
def registry_client(registry_app: FastAPI) -> TestClient:
    return TestClient(registry_app)


def test_missing_route_returns_envelope(
    monkeypatch,
    registry_headers: Dict[str, str],
) -> None:
    class MissingTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no route")

    monkeypatch.setattr(
        "engines.registry.repository.TabularStoreService",
        MissingTabular,
    )
    set_component_registry_service(ComponentRegistryService())

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/registry/components", headers=registry_headers)
    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "component_registry.missing_route"
    assert payload["error"]["http_status"] == 503


def test_components_etag_caching(
    registry_client: TestClient,
    registry_headers: Dict[str, str],
    registry_service: ComponentRegistryService,
    context: RequestContext,
) -> None:
    registry_service.save_component(
        context,
        {"id": "component-a", "version": 1, "metadata": {"tier": "alpha"}},
    )
    response = registry_client.get("/registry/components", headers=registry_headers)
    assert response.status_code == 200
    first_etag = response.headers.get("etag")
    assert first_etag

    cached = registry_client.get(
        "/registry/components",
        headers={**registry_headers, "If-None-Match": first_etag},
    )
    assert cached.status_code == 304
    assert cached.headers.get("etag") == first_etag


def test_registry_persistence(
    fake_tabular,
    context: RequestContext,
) -> None:
    service = ComponentRegistryService()
    service.save_component(
        context,
        {"id": "persistence-comp", "version": 3, "metadata": {"tier": "beta"}},
    )
    service.save_atom(
        context,
        {
            "id": "persistence-atom",
            "version": 2,
            "token_surface": ["surface-registry"],
        },
    )

    reloaded = ComponentRegistryService()
    components = reloaded.get_components(context)
    atoms = reloaded.get_atoms(context)

    assert len(components.components) == 1
    assert components.components[0].id == "persistence-comp"
    assert components.version == 3
    assert len(atoms.atoms) == 1
    assert atoms.atoms[0].id == "persistence-atom"
    assert atoms.version == 2


def test_invalid_atom_spec_returns_envelope(
    registry_client: TestClient,
    registry_headers: Dict[str, str],
    registry_service: ComponentRegistryService,
    context: RequestContext,
) -> None:
    registry_service.repo.save_atom(context, {"id": "bad-atom"})

    response = registry_client.get("/registry/atoms", headers=registry_headers)
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "component_registry.invalid_atom_spec"
    assert payload["error"]["http_status"] == 400
    assert payload["error"]["details"]["entry"] == "bad-atom"
