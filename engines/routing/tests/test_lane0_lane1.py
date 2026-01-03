"""Test Lane 0 + Lane 1 implementation: surface normalization + routing registry."""
import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from engines.common.surface_normalizer import normalize_surface_id
from engines.routing.registry import (
    FileSystemRoutingRegistry,
    InMemoryRoutingRegistry,
    ResourceRoute,
)
from engines.routing.resource_kinds import VECTOR_STORE, OBJECT_STORE


class TestSurfaceNormalization:
    """Tests for Lane 0: Surface normalization."""
    
    def test_normalize_squared_variants(self):
        """Test that all SQUARED² variants normalize to squared2."""
        aliases = ["squared", "squared2", "SQUARED", "SQUARED2", "SQUARED²", "squared²"]
        for alias in aliases:
            assert normalize_surface_id(alias) == "squared2", f"Failed for {alias}"
    
    def test_normalize_none_returns_none(self):
        """Test that None input returns None."""
        assert normalize_surface_id(None) is None
    
    def test_normalize_unknown_surface_passthrough(self):
        """Test that unknown surfaces pass through unchanged."""
        assert normalize_surface_id("custom_surface") == "custom_surface"


class TestResourceRouteNormalization:
    """Tests for surface_id normalization in ResourceRoute."""
    
    def test_route_normalizes_surface_on_init(self):
        """Test that ResourceRoute normalizes surface_id on creation."""
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=OBJECT_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
            surface_id="SQUARED²",  # Alias
        )
        assert route.surface_id == "squared2", "surface_id should be normalized"
    
    def test_route_with_none_surface(self):
        """Test that None surface_id stays None."""
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=VECTOR_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
            surface_id=None,
        )
        assert route.surface_id is None


class TestFileSystemRoutingRegistry:
    """Tests for Lane 1: FileSystem persistence."""
    
    @pytest.fixture
    def temp_registry_dir(self):
        """Create a temporary directory for registry storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_upsert_and_get_route(self, temp_registry_dir):
        """Test that routes are persisted and can be retrieved."""
        registry = FileSystemRoutingRegistry(temp_registry_dir)
        
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=OBJECT_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
            config={"base_dir": "/tmp/storage"},
        )
        
        # Upsert
        registry.upsert_route(route)
        
        # Get
        retrieved = registry.get_route(OBJECT_STORE, "t_demo", "dev")
        assert retrieved is not None
        assert retrieved.id == route.id
        assert retrieved.backend_type == "filesystem"
    
    def test_alias_round_trip(self, temp_registry_dir):
        """Test that alias round-trip works: store with SQUARED², get with squared."""
        registry = FileSystemRoutingRegistry(temp_registry_dir)
        
        # Upsert with alias
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=OBJECT_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
            surface_id="SQUARED²",  # Alias
        )
        registry.upsert_route(route)
        
        # Get with different alias
        retrieved = registry.get_route(OBJECT_STORE, "t_demo", "dev")
        assert retrieved is not None
        # Should both normalize to squared2
        assert retrieved.surface_id == "squared2"
        assert route.surface_id == "squared2"
    
    def test_persistence_survives_restart(self, temp_registry_dir):
        """Test that data persists across registry instances."""
        route_id = str(uuid4())
        
        # Create first registry and upsert
        registry1 = FileSystemRoutingRegistry(temp_registry_dir)
        route = ResourceRoute(
            id=route_id,
            resource_kind=VECTOR_STORE,
            tenant_id="t_system",
            env="dev",
            backend_type="firestore",
            config={"project": "test"},
        )
        registry1.upsert_route(route)
        
        # Create second registry (simulates restart)
        registry2 = FileSystemRoutingRegistry(temp_registry_dir)
        retrieved = registry2.get_route(VECTOR_STORE, "t_system", "dev")
        
        assert retrieved is not None
        assert retrieved.id == route_id
        assert retrieved.backend_type == "firestore"
    
    def test_file_structure_is_deterministic(self, temp_registry_dir):
        """Test that file paths follow deterministic structure."""
        registry = FileSystemRoutingRegistry(temp_registry_dir)
        
        route = ResourceRoute(
            id=str(uuid4()),
            resource_kind=OBJECT_STORE,
            tenant_id="t_demo",
            env="dev",
            backend_type="filesystem",
        )
        registry.upsert_route(route)
        
        # Check that file exists at expected path
        expected_path = (
            Path(temp_registry_dir) / "object_store" / "t_demo" / "dev" / "_.json"
        )
        assert expected_path.exists(), f"File not found at {expected_path}"
        
        # Check file contains valid JSON
        with open(expected_path) as f:
            data = json.load(f)
        assert data["resource_kind"] == "object_store"
        assert data["tenant_id"] == "t_demo"
    
    def test_list_routes_with_filters(self, temp_registry_dir):
        """Test listing routes with optional filters."""
        registry = FileSystemRoutingRegistry(temp_registry_dir)
        
        # Create multiple routes
        for kind in [OBJECT_STORE, VECTOR_STORE]:
            route = ResourceRoute(
                id=str(uuid4()),
                resource_kind=kind,
                tenant_id="t_demo",
                env="dev",
                backend_type="filesystem",
            )
            registry.upsert_route(route)
        
        # List all
        all_routes = registry.list_routes()
        assert len(all_routes) == 2
        
        # Filter by resource_kind
        obj_routes = registry.list_routes(resource_kind=OBJECT_STORE)
        assert len(obj_routes) == 1
        assert obj_routes[0].resource_kind == OBJECT_STORE
        
        # Filter by tenant
        demo_routes = registry.list_routes(tenant_id="t_demo")
        assert len(demo_routes) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
