from __future__ import annotations

from typing import Dict

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from engines.chat.service.http_transport import register_error_handlers
from engines.common.identity import RequestContext
from engines.config_store.routes import router
from engines.config_store.service import ConfigService, set_config_service
from engines.identity.auth import AuthContext, get_auth_context
from engines.identity.models import App, Surface
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo


@pytest.fixture
def context() -> RequestContext:
    ctx = RequestContext(
        tenant_id="t_conf",
        env="dev",
        mode="saas",
        project_id="proj",
        request_id="req-id",
        user_id="user1",
    )
    ctx.surface_id = "surface-alpha"
    return ctx


@pytest.fixture
def fake_tabular(monkeypatch):
    class FakeTabularStoreService:
        _store: Dict[str, Dict[str, Dict]] = {}

        def __init__(self, context, resource_kind="config_store"):
            self.context = context
            self.resource_kind = resource_kind

        def upsert(self, table_name, key, data):
            table = FakeTabularStoreService._store.setdefault(table_name, {})
            table[key] = data

        def get(self, table_name, key):
            return FakeTabularStoreService._store.get(table_name, {}).get(key)

    FakeTabularStoreService._store = {}
    monkeypatch.setattr("engines.config_store.repository.TabularStoreService", FakeTabularStoreService)
    return FakeTabularStoreService


@pytest.fixture
def service(fake_tabular):
    svc = ConfigService()
    set_config_service(svc)
    return svc


@pytest.fixture(autouse=True)
def identity_repo_setup():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    repo.create_surface(Surface(tenant_id="t_conf", name="default"))
    repo.create_app(App(tenant_id="t_conf", name="default"))
    return repo


def _values(mode: str) -> Dict[str, str]:
    return {"tool_canvas_mode": mode}


def test_put_get_config_per_scope(context: RequestContext, service: ConfigService):
    scopes = ["system", "tenant", "surface"]
    for idx, scope in enumerate(scopes, start=1):
        mode_value = "A" if idx % 2 == 0 else "B"
        identifier = "system" if scope == "system" else (context.tenant_id if scope == "tenant" else context.surface_id)
        saved = service.save_config(context, scope, identifier, version=idx, values=_values(mode_value))
        assert saved.version == idx
        assert saved.values["tool_canvas_mode"] == mode_value

        fetched = service.get_config(context, scope, identifier)
        assert fetched.version == idx
        assert fetched.values["tool_canvas_mode"] == mode_value


def test_missing_route_throws_503(monkeypatch, context: RequestContext):
    class MissingTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("route missing")

    monkeypatch.setattr("engines.config_store.repository.TabularStoreService", MissingTabular)
    service = ConfigService()

    with pytest.raises(HTTPException) as exc:
        service.get_config(context, "system", "system")

    detail = exc.value.detail["error"]
    assert exc.value.status_code == 503
    assert detail["code"] == "config_store.missing_route"


def _mock_auth_context() -> AuthContext:
    return AuthContext(
        user_id="user-test",
        email="test@example.com",
        tenant_ids=["t_conf"],
        default_tenant_id="t_conf",
        role_map={"t_conf": "owner"},
        provider="test",
        claims={},
    )


@pytest.fixture
def config_headers() -> Dict[str, str]:
    return {
        "X-Tenant-Id": "t_conf",
        "X-Mode": "saas",
        "X-Project-Id": "proj",
        "X-Surface-Id": "surface-alpha",
    }


@pytest.fixture
def config_app(service: ConfigService) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_auth_context] = lambda: _mock_auth_context()
    return app


@pytest.fixture
def config_client(config_app: FastAPI) -> TestClient:
    return TestClient(config_app)


def test_config_effective_overlay_precedence(
    context: RequestContext,
    service: ConfigService,
    config_client: TestClient,
    config_headers: Dict[str, str],
) -> None:
    service.save_config(
        context,
        "system",
        "system",
        version=1,
        values={"tool_canvas_mode": "A", "feature": "system"},
    )
    service.save_config(
        context,
        "tenant",
        context.tenant_id,
        version=2,
        values={"feature": "tenant", "tenant_only": True},
    )
    service.save_config(
        context,
        "surface",
        context.surface_id,
        version=3,
        values={"feature": "surface", "surface_only": True},
    )

    response = config_client.get("/config/effective", headers=config_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 3
    assert payload["values"]["feature"] == "surface"
    assert payload["values"]["tenant_only"] is True
    assert payload["values"]["surface_only"] is True
    assert payload["values"]["tool_canvas_mode"] == "A"
    assert payload["sources"] == {"system": 1, "tenant": 2, "surface": 3}


def test_config_put_invalid_tool_canvas_mode_emits_envelope(
    config_client: TestClient,
    config_headers: Dict[str, str],
) -> None:
    response = config_client.put(
        "/config/system",
        headers=config_headers,
        json={"version": 1, "values": {"tool_canvas_mode": "X"}},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "config.invalid_tool_canvas_mode"
    assert payload["error"]["http_status"] == 400


def test_config_invalid_scope_emits_envelope(
    config_client: TestClient,
    config_headers: Dict[str, str],
) -> None:
    response = config_client.get("/config/invalid-scope", headers=config_headers)
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "config.invalid_scope"


def test_config_missing_route_returns_envelope(
    monkeypatch,
    config_headers: Dict[str, str],
) -> None:
    class MissingTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("route missing")

    monkeypatch.setattr(
        "engines.config_store.repository.TabularStoreService",
        MissingTabular,
    )
    set_config_service(ConfigService())

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_auth_context] = lambda: _mock_auth_context()
    client = TestClient(app)

    response = client.get("/config/system", headers=config_headers)
    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "config_store.missing_route"
    assert payload["error"]["http_status"] == 503
