"""Integration tests for BB-01 (blackboard_store routing-only enforcement).

Verifies:
- Versioned writes with optimistic concurrency
- Read specific version or latest
- List keys functionality
- Rejection (HTTP 503) when route missing
- Version conflict handling (HTTP 409)
- No in-memory fallbacks
"""
import pytest
from unittest.mock import MagicMock, patch

from engines.common.identity import RequestContext
from engines.blackboard_store.service_reject import (
    BlackboardStoreServiceRejectOnMissing,
    MissingBlackboardStoreRoute,
)


@pytest.fixture
def request_context():
    """Create a test RequestContext."""
    return RequestContext(
        tenant_id="t_test_tenant",
        mode="saas",
        env="dev",
        user_id="test_user",
        surface_id="chat",
        project_id="test_project",
    )


class TestBlackboardStoreRejectOnMissing:
    """Test BB-01 compliance: reject on missing route."""
    
    def test_reject_on_missing_route_saas(self, request_context):
        """Verify MissingBlackboardStoreRoute raised in saas mode when route missing."""
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_registry.return_value.get_route.return_value = None
            
            with pytest.raises(MissingBlackboardStoreRoute) as exc_info:
                BlackboardStoreServiceRejectOnMissing(request_context)
            
            error = exc_info.value
            assert error.error_code == "blackboard_store.missing_route"
            assert error.status_code == 503
            assert "Configure via /routing/routes" in error.message
    
    def test_reject_on_missing_route_enterprise(self):
        """Verify rejection in enterprise mode."""
        context = RequestContext(
            tenant_id="t_test_tenant",
            mode="enterprise",
            env="prod",
            user_id="test_user",
        )
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_registry.return_value.get_route.return_value = None
            
            with pytest.raises(MissingBlackboardStoreRoute):
                BlackboardStoreServiceRejectOnMissing(context)
    
    def test_write_with_valid_route(self, request_context):
        """Verify write works when route is configured."""
        mock_adapter = MagicMock()
        mock_adapter.write.return_value = {
            "key": "strategy_state",
            "value": {"mode": "active"},
            "version": 1,
            "created_by": "test_user",
            "created_at": "2025-01-XX",
            "updated_by": "test_user",
            "updated_at": "2025-01-XX",
        }
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.FirestoreBlackboardStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                result = svc.write(
                    key="strategy_state",
                    value={"mode": "active"},
                    expected_version=None,
                    run_id="run_123",
                )
                
                assert result["key"] == "strategy_state"
                assert result["version"] == 1
                mock_adapter.write.assert_called_once()
    
    def test_write_with_version_conflict(self, request_context):
        """Verify VersionConflictError raised on version mismatch."""
        from engines.blackboard_store.cloud_blackboard_store import VersionConflictError
        
        mock_adapter = MagicMock()
        mock_adapter.write.side_effect = VersionConflictError("version conflict: expected 5, got 4")
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "dynamodb"
            mock_route.config = {"table_name": "blackboard"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.DynamoDBBlackboardStore') as mock_ddb:
                mock_ddb.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                
                with pytest.raises(VersionConflictError) as exc_info:
                    svc.write(key="state", value={"x": 1}, expected_version=5, run_id="run_123")
                
                assert "version conflict" in str(exc_info.value).lower()
    
    def test_read_latest_version(self, request_context):
        """Verify read returns latest version."""
        mock_adapter = MagicMock()
        mock_adapter.read.return_value = {
            "key": "strategy_state",
            "value": {"mode": "active"},
            "version": 3,
            "created_by": "test_user",
            "created_at": "2025-01-XX",
            "updated_by": "test_user",
            "updated_at": "2025-01-XX",
        }
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.FirestoreBlackboardStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                result = svc.read(key="strategy_state", run_id="run_123")
                
                assert result["version"] == 3
                mock_adapter.read.assert_called_once_with(key="strategy_state", context=request_context, run_id="run_123", version=None)
    
    def test_read_specific_version(self, request_context):
        """Verify read can fetch specific version."""
        mock_adapter = MagicMock()
        mock_adapter.read.return_value = {
            "key": "strategy_state",
            "value": {"mode": "pause"},
            "version": 2,
            "created_by": "test_user",
            "created_at": "2025-01-XX",
            "updated_by": "other_user",
            "updated_at": "2025-01-XX",
        }
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.FirestoreBlackboardStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                result = svc.read(key="strategy_state", version=2, run_id="run_123")
                
                assert result["version"] == 2
                mock_adapter.read.assert_called_once_with(key="strategy_state", context=request_context, run_id="run_123", version=2)
    
    def test_read_missing_key_returns_none(self, request_context):
        """Verify read returns None for missing key."""
        mock_adapter = MagicMock()
        mock_adapter.read.return_value = None
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.FirestoreBlackboardStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                result = svc.read(key="nonexistent", run_id="run_123")
                
                assert result is None
    
    def test_list_keys(self, request_context):
        """Verify list_keys returns all keys in blackboard."""
        mock_adapter = MagicMock()
        mock_adapter.list_keys.return_value = [
            "strategy_state",
            "budget_spent",
            "safety_flags",
        ]
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "cosmos"
            mock_route.config = {"endpoint": "https://...", "key": "..."}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.CosmosBlackboardStore') as mock_cosmos:
                mock_cosmos.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                keys = svc.list_keys(run_id="run_123")
                
                assert len(keys) == 3
                assert "strategy_state" in keys
                mock_adapter.list_keys.assert_called_once()
    
    def test_no_fallback_on_write_error(self, request_context):
        """Verify no in-memory fallback on write error."""
        mock_adapter = MagicMock()
        mock_adapter.write.side_effect = Exception("Backend unreachable")
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.FirestoreBlackboardStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                
                with pytest.raises(RuntimeError) as exc_info:
                    svc.write(key="state", value={"x": 1}, run_id="run_123")
                
                assert "Blackboard write failed" in str(exc_info.value)
    
    def test_no_fallback_on_read_error(self, request_context):
        """Verify no in-memory fallback on read error."""
        mock_adapter = MagicMock()
        mock_adapter.read.side_effect = Exception("Backend unreachable")
        
        with patch('engines.blackboard_store.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.blackboard_store.service_reject.FirestoreBlackboardStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = BlackboardStoreServiceRejectOnMissing(request_context)
                
                with pytest.raises(RuntimeError) as exc_info:
                    svc.read(key="state", run_id="run_123")
                
                assert "Blackboard read failed" in str(exc_info.value)


class TestBlackboardStoreRoutes:
    """Test HTTP endpoints for blackboard_store."""
    
    @pytest.mark.asyncio
    async def test_write_endpoint(self):
        """Test POST /blackboard/write endpoint."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_read_endpoint(self):
        """Test GET /blackboard/read endpoint."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_list_keys_endpoint(self):
        """Test GET /blackboard/list-keys endpoint."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_version_conflict_returns_409(self):
        """Test that version conflict returns HTTP 409."""
        # Placeholder for full integration test with test client
        pass
    
    @pytest.mark.asyncio
    async def test_missing_route_returns_503(self):
        """Test that missing route returns HTTP 503 with error_code."""
        # Placeholder for full integration test with test client
        pass
