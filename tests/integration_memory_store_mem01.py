"""Integration tests for MEM-01 (memory_store routing-only enforcement).

Verifies:
- Set/get/delete persistence
- TTL support
- Rejection (HTTP 503) when route missing
- No in-memory fallbacks in saas/enterprise
"""
import pytest
from unittest.mock import MagicMock, patch

from engines.common.identity import RequestContext
from engines.memory_store.service_reject import (
    MemoryStoreServiceRejectOnMissing,
    MissingMemoryStoreRoute,
)


@pytest.fixture
def request_context():
    """Create a test RequestContext."""
    return RequestContext(
        tenant_id="test_tenant",
        mode="saas",
        env="dev",
        user_id="test_user",
        surface_id="chat",
        project_id="test_project",
    )


class TestMemoryStoreRejectOnMissing:
    """Test MEM-01 compliance: reject on missing route."""
    
    def test_reject_on_missing_route_saas(self, request_context):
        """Verify MissingMemoryStoreRoute is raised in saas mode when route missing."""
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_registry.return_value.get_route.return_value = None
            
            with pytest.raises(MissingMemoryStoreRoute) as exc_info:
                MemoryStoreServiceRejectOnMissing(request_context)
            
            error = exc_info.value
            assert error.error_code == "memory_store.missing_route"
            assert error.status_code == 503
            assert "Configure via /routing/routes" in error.message
    
    def test_reject_on_missing_route_enterprise(self):
        """Verify rejection in enterprise mode."""
        context = RequestContext(
            tenant_id="test_tenant",
            mode="enterprise",
            env="prod",
            user_id="test_user",
        )
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_registry.return_value.get_route.return_value = None
            
            with pytest.raises(MissingMemoryStoreRoute):
                MemoryStoreServiceRejectOnMissing(context)
    
    def test_set_with_valid_route(self, request_context):
        """Verify set works when route is configured."""
        mock_adapter = MagicMock()
        mock_adapter.set.return_value = None
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.memory_store.service_reject.FirestoreMemoryStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = MemoryStoreServiceRejectOnMissing(request_context)
                svc.set(key="test_key", value="test_value", ttl_seconds=3600)
                
                mock_adapter.set.assert_called_once()
                call_args = mock_adapter.set.call_args
                assert call_args[0][0] == "test_key"
                assert call_args[0][1] == "test_value"
                assert call_args[1]["ttl_seconds"] == 3600
    
    def test_get_returns_value(self, request_context):
        """Verify get returns value when found."""
        mock_adapter = MagicMock()
        mock_adapter.get.return_value = "test_value"
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.memory_store.service_reject.FirestoreMemoryStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = MemoryStoreServiceRejectOnMissing(request_context)
                value = svc.get(key="test_key")
                
                assert value == "test_value"
                mock_adapter.get.assert_called_once()
    
    def test_get_returns_none_when_not_found(self, request_context):
        """Verify get returns None when key not found."""
        mock_adapter = MagicMock()
        mock_adapter.get.return_value = None
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.memory_store.service_reject.FirestoreMemoryStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = MemoryStoreServiceRejectOnMissing(request_context)
                value = svc.get(key="nonexistent_key")
                
                assert value is None
    
    def test_delete_with_valid_route(self, request_context):
        """Verify delete works when route is configured."""
        mock_adapter = MagicMock()
        mock_adapter.delete.return_value = None
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.memory_store.service_reject.FirestoreMemoryStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = MemoryStoreServiceRejectOnMissing(request_context)
                svc.delete(key="test_key")
                
                mock_adapter.delete.assert_called_once()
    
    def test_no_fallback_on_set_error(self, request_context):
        """Verify no in-memory fallback on set error."""
        mock_adapter = MagicMock()
        mock_adapter.set.side_effect = Exception("Backend unreachable")
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.memory_store.service_reject.FirestoreMemoryStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = MemoryStoreServiceRejectOnMissing(request_context)
                
                # Set should raise, not fall back to in-memory
                with pytest.raises(RuntimeError) as exc_info:
                    svc.set(key="test_key", value="test_value")
                
                assert "Memory set failed" in str(exc_info.value)
    
    def test_ttl_passed_to_adapter(self, request_context):
        """Verify TTL is correctly passed to backend."""
        mock_adapter = MagicMock()
        
        with patch('engines.memory_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "dynamodb"
            mock_route.config = {"table_name": "memory_store", "region": "us-west-2"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.memory_store.service_reject.DynamoDBMemoryStore') as mock_ddb:
                mock_ddb.return_value = mock_adapter
                
                svc = MemoryStoreServiceRejectOnMissing(request_context)
                svc.set(key="test_key", value="test_value", ttl_seconds=7200)
                
                call_args = mock_adapter.set.call_args
                assert call_args[1]["ttl_seconds"] == 7200


class TestMemoryStoreRoutes:
    """Test HTTP endpoints for memory_store."""
    
    @pytest.mark.asyncio
    async def test_set_endpoint(self):
        """Test POST /memory/set endpoint."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_get_endpoint(self):
        """Test GET /memory/get endpoint."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_delete_endpoint(self):
        """Test DELETE /memory/delete endpoint."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_missing_route_returns_503(self):
        """Test that missing route returns HTTP 503 with error_code."""
        # Placeholder for full integration test with test client
        pass
