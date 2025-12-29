import pytest
import os
import sys
import importlib
from unittest import mock

# Clear environment variables to simulate "missing config" state
@pytest.fixture
def clean_env():
    # We must clear these to ensure we trigger the failure paths
    keys_to_remove = [
        "RAW_BUCKET", "IDENTITY_BACKEND", 
        "CHAT_BUS_BACKEND", "NEXUS_BACKEND",
        "REDIS_HOST", "REDIS_PORT",
        "MEMORY_BACKEND", "BUDGET_BACKEND",
    ]
    old_environ = {}
    for k in keys_to_remove:
        if k in os.environ:
            old_environ[k] = os.environ[k]
            del os.environ[k]
            
    yield
    
    # Restore
    os.environ.update(old_environ)

def test_media_service_fails_fast_without_config(clean_env):
    """MediaService should fail if S3 bucket is not configured."""
    from engines.media_v2 import service
    importlib.reload(service)
    from engines.media_v2.service import S3MediaStorage
    
    with pytest.raises(RuntimeError, match="RAW_BUCKET config missing"):
        S3MediaStorage()

def test_identity_fails_fast(clean_env):
    """Identity default repo should fail on access if backend not set."""
    from engines.identity import state
    importlib.reload(state)
    
    # Import succeeds now (lazy)
    repo = state.identity_repo
    
    # Access triggers crash
    with pytest.raises(RuntimeError, match="IDENTITY_BACKEND must be 'firestore'"):
        getattr(repo, "get_user")

def test_chat_fails_fast(clean_env):
    """Chat bus should fail on access if backend not set."""
    from engines.chat.service import transport_layer
    importlib.reload(transport_layer)
    
    bus = transport_layer.bus
    
    with pytest.raises(RuntimeError, match="not allowed in Real Infra mode"):
        getattr(bus, "list_threads")

def test_memory_service_fails_fast(clean_env):
    """MemoryService should fail when MEMORY_BACKEND is not set to firestore."""
    from engines.memory import service as memory_service
    importlib.reload(memory_service)

    with pytest.raises(RuntimeError, match="MEMORY_BACKEND must be set to 'firestore'"):
        memory_service.MemoryService()

def test_nexus_memory_service_fails_fast(clean_env):
    """Nexus SessionMemoryService should fail without a durable backend."""
    from engines.nexus.memory import service as nexus_memory_service
    importlib.reload(nexus_memory_service)

    with pytest.raises(RuntimeError, match="MEMORY_BACKEND must be set to 'firestore'"):
        nexus_memory_service.SessionMemoryService()

def test_budget_repo_fails_fast(clean_env):
    """BudgetService should fail when BUDGET_BACKEND is not configured."""
    from engines.budget import service as budget_service
    importlib.reload(budget_service)

    with pytest.raises(RuntimeError, match="BUDGET_BACKEND must be set to 'firestore'"):
        budget_service.BudgetService()

def test_nexus_fails_fast_on_memory(clean_env):
    """Nexus should fail if backend is explicitly memory."""
    from engines.nexus import backends
    
    with mock.patch.dict(os.environ, {"NEXUS_BACKEND": "memory"}):
        with pytest.raises(RuntimeError, match="not allowed in Real Infra mode"):
            importlib.reload(backends)
            backends.get_backend()

def test_nexus_fails_unknown(clean_env):
    """Nexus should fail if backend is unknown."""
    from engines.nexus import backends
    
    with mock.patch.dict(os.environ, {"NEXUS_BACKEND": "alien_tech"}):
        with pytest.raises(RuntimeError, match="unsupported NEXUS_BACKEND"):
             importlib.reload(backends)
             backends.get_backend()


# ===== Lane 3: Routing Registry Tests =====

def test_routing_registry_missing_resource_kind():
    """Test that routing registry raises MissingRoutingConfig when resource not found."""
    from engines.routing.registry import (
        InMemoryRoutingRegistry,
        set_routing_registry,
        MissingRoutingConfig,
    )
    from engines.routing.manager import get_route_config
    
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    with pytest.raises(MissingRoutingConfig):
        get_route_config("nonexistent", "t_system", "prod", fail_fast=True)


def test_routing_registry_backend_type_validation():
    """Test that routing registry allows valid backend types."""
    from uuid import uuid4
    from engines.routing.registry import (
        ResourceRoute,
        InMemoryRoutingRegistry,
        set_routing_registry,
    )
    from engines.routing.manager import get_backend_type
    
    registry = InMemoryRoutingRegistry()
    set_routing_registry(registry)
    
    # Feature flags should be firestore
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind="feature_flags",
        tenant_id="t_system",
        env="prod",
        backend_type="firestore",
        required=True,
    )
    registry.upsert_route(route)
    
    backend = get_backend_type("feature_flags", "t_system", "prod", fail_fast=True)
    assert backend == "firestore"
