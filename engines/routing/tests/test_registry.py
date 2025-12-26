"""Tests for routing registry CRUD and validation."""
import pytest
from uuid import uuid4

from engines.routing.registry import (
    ResourceRoute,
    InMemoryRoutingRegistry,
    MissingRoutingConfig,
)


@pytest.fixture
def registry():
    """In-memory registry for tests."""
    return InMemoryRoutingRegistry()


def test_upsert_and_get_route(registry):
    """Test creating and retrieving a route."""
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        config={"collection": "feature_flags"},
    )
    
    created = registry.upsert_route(route)
    assert created.id == route.id
    
    retrieved = registry.get_route("feature_flags", "t_system", "prod")
    assert retrieved is not None
    assert retrieved.backend_type == "firestore"
    assert retrieved.config["collection"] == "feature_flags"


def test_get_route_not_found(registry):
    """Test retrieving nonexistent route."""
    result = registry.get_route("nonexistent", "t_system", "prod")
    assert result is None


def test_list_routes_all(registry):
    """Test listing all routes."""
    r1 = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
    )
    r2 = ResourceRoute(
        id=str(uuid4()),
        resource_kind="strategy_lock",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
    )
    
    registry.upsert_route(r1)
    registry.upsert_route(r2)
    
    routes = registry.list_routes()
    assert len(routes) == 2


def test_list_routes_by_kind(registry):
    """Test filtering routes by resource_kind."""
    r1 = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
    )
    r2 = ResourceRoute(
        id=str(uuid4()),
        resource_kind="strategy_lock",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
    )
    
    registry.upsert_route(r1)
    registry.upsert_route(r2)
    
    routes = registry.list_routes(resource_kind="feature_flags")
    assert len(routes) == 1
    assert routes[0].resource_kind == "feature_flags"


def test_list_routes_by_tenant(registry):
    """Test filtering routes by tenant_id."""
    r1 = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
    )
    r2 = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_acme",
        env="prod",
        backend_type="firestore",
    )
    
    registry.upsert_route(r1)
    registry.upsert_route(r2)
    
    routes = registry.list_routes(tenant_id="t_system")
    assert len(routes) == 1
    assert routes[0].tenant_id == "t_system"


def test_delete_route(registry):
    """Test deleting a route."""
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
    )
    
    registry.upsert_route(route)
    assert registry.get_route("feature_flags", "t_system", "prod") is not None
    
    registry.delete_route("feature_flags", "t_system", "prod")
    assert registry.get_route("feature_flags", "t_system", "prod") is None


def test_route_with_project_id(registry):
    """Test route with project_id scope."""
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_acme",
        env="prod",
        project_id="proj_123",
        backend_type="firestore",
    )
    
    registry.upsert_route(route)
    
    # Exact match with project_id
    retrieved = registry.get_route("feature_flags", "t_acme", "prod", project_id="proj_123")
    assert retrieved is not None
    
    # Different project_id returns None
    different = registry.get_route("feature_flags", "t_acme", "prod", project_id="proj_456")
    assert different is None
    
    # No project_id specified returns None (exact key match)
    no_project = registry.get_route("feature_flags", "t_acme", "prod")
    assert no_project is None


def test_route_required_flag(registry):
    """Test that required flag is preserved."""
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        required=True,
    )
    
    created = registry.upsert_route(route)
    retrieved = registry.get_route("feature_flags", "t_system", "prod")
    assert retrieved.required is True


def test_upsert_updates_existing(registry):
    """Test that upsert updates existing routes."""
    route1 = ResourceRoute(
        id="route-1",
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        config={"collection": "old"},
    )
    
    registry.upsert_route(route1)
    
    # Update with same key, different config
    route2 = ResourceRoute(
        id="route-1",
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        config={"collection": "new"},
    )
    
    registry.upsert_route(route2)
    
    # Should have updated config
    retrieved = registry.get_route("feature_flags", "t_system", "prod")
    assert retrieved.config["collection"] == "new"
