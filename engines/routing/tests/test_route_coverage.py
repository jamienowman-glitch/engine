from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from engines.routing.routes import router, CANONICAL_RESOURCE_KINDS
from engines.routing.registry import (
    InMemoryRoutingRegistry,
    ResourceRoute,
    set_routing_registry,
    routing_registry,
)


@pytest.fixture(autouse=True)
def in_memory_registry():
    registry = InMemoryRoutingRegistry()
    prev = routing_registry()
    set_routing_registry(registry)
    yield registry
    set_routing_registry(prev)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _headers():
    return {
        "X-Mode": "lab",
        "X-Tenant-Id": "t_diag",
        "X-Project-Id": "p_diag",
        "X-Request-Id": "req_diag",
    }


def test_route_coverage_reports_missing_routes(client):
    resp = client.get("/routing/diagnostics/coverage/t_diag/dev", headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == "t_diag"
    assert body["env"] == "dev"
    resources = {entry["resource_kind"]: entry for entry in body["resources"]}
    assert set(resources) == set(CANONICAL_RESOURCE_KINDS)
    for kind, entry in resources.items():
        assert entry["status"] == "missing"
        assert entry["error"]["code"] == f"{kind}.missing_route"
        assert entry["error"]["http_status"] == 503


def test_route_coverage_includes_available_route(registry, client):
    route = ResourceRoute(
        id="rid",
        resource_kind="chat_store",
        tenant_id="t_diag",
        env="dev",
        backend_type="firestore",
        config={},
    )
    registry.upsert_route(route)
    resp = client.get("/routing/diagnostics/coverage/t_diag/dev", headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    resources = {entry["resource_kind"]: entry for entry in body["resources"]}
    entry = resources["chat_store"]
    assert entry["status"] == "available"
    assert entry["backend_type"] == "firestore"
