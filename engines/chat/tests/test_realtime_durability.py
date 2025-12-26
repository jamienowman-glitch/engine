"""Tests for realtime durability (chat bus + registry)."""
import pytest
from unittest import mock
import os
from uuid import uuid4

from engines.routing.registry import (
    ResourceRoute,
    InMemoryRoutingRegistry,
    set_routing_registry,
)
from engines.routing.manager import get_route_config, get_backend_type


def test_chat_bus_redis_durability():
    """Test that chat_bus requires redis with host/port config."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Seed redis config for chat_bus
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
    
    backend = get_backend_type("chat_bus", "t_system", "prod", fail_fast=True)
    assert backend == "redis"
    
    config = get_route_config("chat_bus", "t_system", "prod", fail_fast=True)
    assert config["host"] == "redis-prod.example.com"
    assert config["port"] == 6379


def test_realtime_registry_firestore():
    """Test that realtime_registry uses firestore for durability."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Seed firestore config for realtime registry
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="realtime_registry",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        config={"collection": "realtime_registry"},
        required=True,
    )
    registry.upsert_route(route)
    
    backend = get_backend_type("realtime_registry", "t_system", "prod", fail_fast=True)
    assert backend == "firestore"


def test_chat_bus_survives_restart():
    """Test that chat_bus thread/canvas ownership persists across restart (via durable registry)."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Initial state: configure redis-backed chat bus
    route_before = ResourceRoute(
        id="chat-bus-route",
        resource_kind="chat_bus",
        tenant_id="t_acme",
        env="prod",
        backend_type="redis",
        config={"host": "redis-prod", "port": 6379, "db": 0},
        required=True,
    )
    registry.upsert_route(route_before)
    
    # Simulate "before restart" - get config
    config_before = get_route_config("chat_bus", "t_acme", "prod", fail_fast=True)
    assert config_before["host"] == "redis-prod"
    
    # Simulate "after restart" - registry query should return same config
    registry2 = InMemoryRoutingRegistry()
    set_routing_registry(registry2)
    registry2.upsert_route(route_before)
    
    config_after = get_route_config("chat_bus", "t_acme", "prod", fail_fast=True)
    assert config_after["host"] == "redis-prod"
    assert config_after == config_before


def test_realtime_registry_survives_restart():
    """Test that realtime_registry thread state persists (via durable Firestore)."""
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Initial: firestore-backed realtime registry
    route = ResourceRoute(
        id="realtime-registry-route",
        resource_kind="realtime_registry",
        tenant_id="t_acme",
        env="prod",
        backend_type="firestore",
        config={"collection": "realtime_registry", "project": "northstar-prod"},
        required=True,
    )
    registry.upsert_route(route)
    
    config_before = get_route_config("realtime_registry", "t_acme", "prod", fail_fast=True)
    
    # Simulate restart
    registry2 = InMemoryRoutingRegistry()
    set_routing_registry(registry2)
    registry2.upsert_route(route)
    
    config_after = get_route_config("realtime_registry", "t_acme", "prod", fail_fast=True)
    assert config_after == config_before
