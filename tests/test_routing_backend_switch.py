"""Test that backend can be switched via routing registry without redeploy."""
import pytest
from uuid import uuid4

from engines.routing.registry import (
    ResourceRoute,
    InMemoryRoutingRegistry,
    set_routing_registry,
)
from engines.routing.manager import get_backend_type, get_route_config


def test_backend_switch_feature_flags():
    """Test switching feature_flags backend via registry update."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Initial state: firestore backend
    route1 = ResourceRoute(
        id="route-ff-1",
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        config={"collection": "feature_flags"},
        required=True,
    )
    registry.upsert_route(route1)
    
    # First request uses firestore
    backend = get_backend_type("feature_flags", "t_system", "prod", fail_fast=True)
    assert backend == "firestore"
    config = get_route_config("feature_flags", "t_system", "prod", fail_fast=True)
    assert config["collection"] == "feature_flags"
    
    # Now switch to test/memory backend (simulating A/B test or rollback)
    route2 = ResourceRoute(
        id="route-ff-1",
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="memory",
        config={"max_flags": 10000},
        required=True,
    )
    registry.upsert_route(route2)  # Update
    
    # Second request uses memory (no redeploy!)
    backend = get_backend_type("feature_flags", "t_system", "prod", fail_fast=True)
    assert backend == "memory"
    config = get_route_config("feature_flags", "t_system", "prod", fail_fast=True)
    assert config["max_flags"] == 10000


def test_backend_switch_rate_limit():
    """Test switching rate_limit backend via registry update."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Initial: firestore
    route1 = ResourceRoute(
        id="route-rl-1",
        resource_kind="rate_limit",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        config={"collection": "rate_limits"},
        required=True,
    )
    registry.upsert_route(route1)
    
    backend = get_backend_type("rate_limit", "t_system", "prod", fail_fast=True)
    assert backend == "firestore"
    
    # Switch to redis (for faster lookups in A/B test)
    route2 = ResourceRoute(
        id="route-rl-1",
        resource_kind="rate_limit",
        tenant_id="t_system",
        env="prod",
        backend_type="redis",
        config={"host": "redis-prod.example.com", "port": 6379},
        required=True,
    )
    registry.upsert_route(route2)  # Update
    
    backend = get_backend_type("rate_limit", "t_system", "prod", fail_fast=True)
    assert backend == "redis"
    config = get_route_config("rate_limit", "t_system", "prod", fail_fast=True)
    assert config["host"] == "redis-prod.example.com"


def test_backend_switch_per_tenant():
    """Test that different tenants can use different backends."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Tenant A uses firestore
    route_a = ResourceRoute(
        id="route-ff-a",
        resource_kind="feature_flags",
        tenant_id="t_acme",
        env="prod",
        backend_type="firestore",
        required=True,
    )
    registry.upsert_route(route_a)
    
    # Tenant B uses memory (maybe beta customer)
    route_b = ResourceRoute(
        id="route-ff-b",
        resource_kind="feature_flags",
        tenant_id="t_beta",
        env="prod",
        backend_type="memory",
        required=True,
    )
    registry.upsert_route(route_b)
    
    # Verify both work independently
    backend_a = get_backend_type("feature_flags", "t_acme", "prod", fail_fast=True)
    backend_b = get_backend_type("feature_flags", "t_beta", "prod", fail_fast=True)
    
    assert backend_a == "firestore"
    assert backend_b == "memory"
    
    # Now upgrade tenant B to firestore
    route_b_upgraded = ResourceRoute(
        id="route-ff-b",
        resource_kind="feature_flags",
        tenant_id="t_beta",
        env="prod",
        backend_type="firestore",
        required=True,
    )
    registry.upsert_route(route_b_upgraded)
    
    backend_b_new = get_backend_type("feature_flags", "t_beta", "prod", fail_fast=True)
    assert backend_b_new == "firestore"


def test_backend_switch_per_env():
    """Test that dev and prod can use different backends."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Dev uses memory for speed
    dev_route = ResourceRoute(
        id="route-ff-dev",
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="dev",
        backend_type="memory",
        required=True,
    )
    registry.upsert_route(dev_route)
    
    # Prod uses firestore for durability
    prod_route = ResourceRoute(
        id="route-ff-prod",
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        required=True,
    )
    registry.upsert_route(prod_route)
    
    dev_backend = get_backend_type("feature_flags", "t_system", "dev", fail_fast=True)
    prod_backend = get_backend_type("feature_flags", "t_system", "prod", fail_fast=True)
    
    assert dev_backend == "memory"
    assert prod_backend == "firestore"
