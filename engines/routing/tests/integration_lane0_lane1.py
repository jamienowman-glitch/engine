"""Integration test for routing control-plane API (Lane 1)."""
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

# Set environment for testing (use in-memory timeline for testing)
os.environ.setdefault("STREAM_TIMELINE_BACKEND", "memory")

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id
from engines.routing.registry import (
    FileSystemRoutingRegistry,
    ResourceRoute,
    set_routing_registry,
)
from engines.routing.service import RoutingControlPlaneService
from engines.routing.resource_kinds import OBJECT_STORE, VECTOR_STORE
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store


def test_routing_api_alias_roundtrip():
    """Test A: Alias round-trip (upsert with SQUARED², get with squared)."""
    print("\n=== TEST A: Alias Round-Trip ===")
    
    # Setup: use filesystem registry and in-memory timeline for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = FileSystemRoutingRegistry(tmpdir)
        set_routing_registry(registry)
        set_timeline_store(InMemoryTimelineStore())
        
        service = RoutingControlPlaneService()
        ctx = RequestContext(
            tenant_id="t_demo",
            env="dev",
            mode="saas",
        )
        
        # Upsert with SQUARED² alias
        print("1. Upserting route with surface_id=SQUARED²")
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=OBJECT_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
            surface_id="SQUARED²",  # Alias
            config={"base_dir": "/tmp/obj_store"},
        )
        created = service.upsert_route(route, ctx)
        print(f"   ✓ Created route {created.id}")
        print(f"   ✓ surface_id normalized to: {created.surface_id}")
        
        # Get with canonical form
        print("2. Getting route with resource_kind and tenant")
        retrieved = service.get_route(OBJECT_STORE, "t_demo", "dev")
        assert retrieved is not None, "Route not found!"
        print(f"   ✓ Retrieved route {retrieved.id}")
        print(f"   ✓ surface_id: {retrieved.surface_id}")
        
        # Verify both are identical
        assert created.surface_id == retrieved.surface_id == "squared2"
        print("   ✓ Both routes have canonical surface_id='squared2'")
        print("✅ TEST A PASSED: Alias round-trip works!")
        return True


def test_routing_api_persistence():
    """Test B: Persistence (restart server, route survives)."""
    print("\n=== TEST B: Persistence ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        route_id = str(uuid4())
        
        # Instance 1: Create and upsert
        print("1. Instance 1: Creating registry and upserting route")
        registry1 = FileSystemRoutingRegistry(tmpdir)
        set_routing_registry(registry1)
        set_timeline_store(InMemoryTimelineStore())
        
        ctx = RequestContext(
            tenant_id="t_demo",
            env="dev",
            mode="saas",
        )
        
        route = ResourceRoute(
            id=route_id,
            resource_kind=VECTOR_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="firestore",
            config={"project": "test-project"},
        )
        service1 = RoutingControlPlaneService()
        service1.upsert_route(route, ctx)
        print(f"   ✓ Upserted route {route_id}")
        
        # Instance 2: New registry (simulates restart)
        print("2. Instance 2 (simulated restart): Creating new registry")
        registry2 = FileSystemRoutingRegistry(tmpdir)
        set_routing_registry(registry2)
        set_timeline_store(InMemoryTimelineStore())
        
        service2 = RoutingControlPlaneService()
        retrieved = service2.get_route(VECTOR_STORE, "t_demo", "dev")
        
        assert retrieved is not None, "Route did not persist!"
        assert retrieved.id == route_id, "Route ID mismatch!"
        assert retrieved.backend_type == "firestore", "Backend type changed!"
        print(f"   ✓ Retrieved same route {retrieved.id} after restart")
        print(f"   ✓ Backend type: {retrieved.backend_type}")
        print("✅ TEST B PASSED: Persistence works!")
        return True


def test_routing_filesystem_location():
    """Test C: Filesystem persistence location."""
    print("\n=== TEST C: Filesystem Location ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = FileSystemRoutingRegistry(tmpdir)
        set_routing_registry(registry)
        set_timeline_store(InMemoryTimelineStore())
        
        ctx = RequestContext(
            tenant_id="t_demo",
            env="dev",
            mode="saas",
        )
        
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=OBJECT_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
            config={"base_dir": "/tmp/storage"},
        )
        
        service = RoutingControlPlaneService()
        service.upsert_route(route, ctx)
        
        # Check filesystem structure
        expected_path = Path(tmpdir) / "object_store" / "t_demo" / "dev" / "_.json"
        assert expected_path.exists(), f"File not found at {expected_path}"
        print(f"✓ File persisted at: {expected_path}")
        
        # Verify file contents
        with open(expected_path) as f:
            data = json.load(f)
        assert data["resource_kind"] == "object_store"
        assert data["backend_type"] == "filesystem"
        print(f"✓ File contains valid JSON with resource_kind={data['resource_kind']}")
        
        # Real location in production would be var/routing/{resource_kind}/{tenant}/{env}/{project}.json
        print(f"✓ Production location: var/routing/{{resource_kind}}/{{tenant}}/{{env}}/{{project}}.json")
        print("✅ TEST C PASSED: Filesystem location confirmed!")
        return True


def test_surface_normalization_helper():
    """Test Lane 0: Surface normalization helper."""
    print("\n=== TEST Lane 0: Surface Normalization ===")
    
    aliases = ["squared", "squared2", "SQUARED", "SQUARED2", "SQUARED²", "squared²"]
    print("Testing surface aliases:")
    for alias in aliases:
        normalized = normalize_surface_id(alias)
        assert normalized == "squared2", f"Failed for {alias}"
        print(f"  ✓ {alias:15} -> {normalized}")
    
    print("✓ None returns None:")
    assert normalize_surface_id(None) is None
    print(f"  ✓ normalize_surface_id(None) -> None")
    
    print("✓ Unknown surfaces pass through:")
    assert normalize_surface_id("custom") == "custom"
    print(f"  ✓ normalize_surface_id('custom') -> 'custom'")
    
    print("✅ TEST Lane 0 PASSED: Normalization helper works!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 0.5 LANE 0 + LANE 1 INTEGRATION TESTS")
    print("=" * 60)
    
    try:
        test_surface_normalization_helper()
        test_routing_api_alias_roundtrip()
        test_routing_api_persistence()
        test_routing_filesystem_location()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
