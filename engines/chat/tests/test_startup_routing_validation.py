"""Startup routing validation for mounted services."""
import pytest
from unittest.mock import patch
from uuid import uuid4

from engines.routing.registry import (
    ResourceRoute,
    InMemoryRoutingRegistry,
    set_routing_registry,
    MissingRoutingConfig,
)
from engines.routing.manager import get_route_config


# Define the required resource kinds for mounted services
REQUIRED_RESOURCE_KINDS = [
    "feature_flags",
    "strategy_lock",
    "kpi",
    "budget",
    "maybes",
    "memory",
    "analytics_events",
    "rate_limit",
    "firearms",
    "page_content",
    "seo",
    "realtime_registry",
    "chat_bus",
    "nexus_backend",
    "media_v2_storage",
    "raw_storage",
    "timeline",
]


def _seed_registry_for_startup(registry: InMemoryRoutingRegistry, seed: bool = True):
    """Helper to seed registry with all required resource kinds for startup validation."""
    if not seed:
        return
    
    for kind in REQUIRED_RESOURCE_KINDS:
        config = {}
        if kind == "chat_bus":
            config = {"host": "localhost", "port": 6379}
        elif kind == "media_v2_storage":
            config = {"bucket": "test-bucket", "storage_kind": "s3"}
        elif kind == "raw_storage":
            config = {"bucket": "test-raw-bucket"}
        elif kind == "realtime_registry":
            config = {"backend": "firestore"}
        
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=kind,
            tenant_id="t_system",
            env="dev",
            backend_type="firestore" if kind != "chat_bus" else "redis",
            config=config,
            required=True,
        )
        registry.upsert_route(route)


def test_startup_validation_missing_routes():
    """Test that startup fails when required routes are missing."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Try to get a required route without seeding
    with pytest.raises(MissingRoutingConfig):
        get_route_config("feature_flags", "t_system", "dev", fail_fast=True)


def test_startup_validation_all_routes_seeded():
    """Test that startup succeeds when all required routes are seeded."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    _seed_registry_for_startup(registry, seed=True)
    
    # Should not raise
    for kind in REQUIRED_RESOURCE_KINDS:
        config = get_route_config(kind, "t_system", "dev", fail_fast=True)
        assert config is not None


def test_startup_validation_partial_seed_fails():
    """Test that startup fails when only some routes are seeded."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Seed only feature_flags
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="dev",
        backend_type="firestore",
        required=True,
    )
    registry.upsert_route(route)
    
    # Get feature_flags should work
    config = get_route_config("feature_flags", "t_system", "dev", fail_fast=True)
    assert config is not None
    
    # Get strategy_lock should fail
    with pytest.raises(MissingRoutingConfig):
        get_route_config("strategy_lock", "t_system", "dev", fail_fast=True)


def test_startup_validation_with_chat_bus():
    """Test that chat_bus config is properly validated."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="chat_bus",
        tenant_id="t_system",
        env="prod",
        backend_type="redis",
        config={"host": "redis-prod.example.com", "port": 6379},
        required=True,
    )
    registry.upsert_route(route)
    
    config = get_route_config("chat_bus", "t_system", "prod", fail_fast=True)
    assert config["host"] == "redis-prod.example.com"
    assert config["port"] == 6379


def test_startup_validation_with_storage():
    """Test that media_v2_storage config with bucket is validated."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="media_v2_storage",
        tenant_id="t_system",
        env="prod",
        backend_type="s3",
        config={"bucket": "northstar-prod-media", "region": "us-west-2"},
        required=True,
    )
    registry.upsert_route(route)
    
    config = get_route_config("media_v2_storage", "t_system", "prod", fail_fast=True)
    assert config["bucket"] == "northstar-prod-media"
    assert config["region"] == "us-west-2"
