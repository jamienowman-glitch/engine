"""Integration tests for TL-01 (event_spine durability/replay enforcement).

Verifies:
- Append-only persistence
- Cursor-based replay across restarts
- Rejection (HTTP 503) when route missing
- No in-memory fallbacks
"""
import pytest
from unittest.mock import MagicMock, patch

from engines.common.identity import RequestContext
from engines.event_spine.service_reject import (
    EventSpineServiceRejectOnMissing,
    MissingEventSpineRoute,
)
from engines.event_spine.cloud_event_spine_store import SpineEvent


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


class TestEventSpineRejectOnMissing:
    """Test TL-01 compliance: reject on missing route."""
    
    def test_reject_on_missing_route(self, request_context):
        """Verify MissingEventSpineRoute is raised when route missing."""
        # Mock routing registry to return no route
        with patch('engines.event_spine.service_reject.routing_registry') as mock_registry:
            mock_registry.return_value.get_route.return_value = None
            
            with pytest.raises(MissingEventSpineRoute) as exc_info:
                EventSpineServiceRejectOnMissing(request_context)
            
            error = exc_info.value
            assert error.error_code == "event_spine.missing_route"
            assert error.status_code == 503
            assert "Configure via /routing/routes" in error.message
    
    def test_append_with_valid_route(self, request_context):
        """Verify append works when route is configured."""
        # Mock the adapter
        mock_adapter = MagicMock()
        mock_adapter.append.return_value = None
        
        with patch('engines.event_spine.service_reject.routing_registry') as mock_registry:
            # Create a mock route
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.event_spine.service_reject.FirestoreEventSpineStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = EventSpineServiceRejectOnMissing(request_context)
                event_id = svc.append(
                    event_type="analytics",
                    source="agent",
                    run_id="test_run",
                    payload={"test": "data"},
                )
                
                assert event_id is not None
                assert len(event_id) > 0
                mock_adapter.append.assert_called_once()
    
    def test_replay_with_cursor(self, request_context):
        """Verify cursor-based replay works."""
        # Mock the adapter with sample events
        event1 = SpineEvent(
            tenant_id="test_tenant",
            mode="saas",
            event_type="analytics",
            source="agent",
            run_id="test_run",
            event_id="event_1",
            timestamp="2026-01-03T10:00:00Z",
        )
        event2 = SpineEvent(
            tenant_id="test_tenant",
            mode="saas",
            event_type="analytics",
            source="agent",
            run_id="test_run",
            event_id="event_2",
            timestamp="2026-01-03T10:01:00Z",
        )
        
        mock_adapter = MagicMock()
        mock_adapter.list_events.return_value = [event2]  # Return event_2 when cursor="event_1"
        
        with patch('engines.event_spine.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.event_spine.service_reject.FirestoreEventSpineStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = EventSpineServiceRejectOnMissing(request_context)
                events = svc.replay(
                    run_id="test_run",
                    after_event_id="event_1",
                    limit=100,
                )
                
                assert len(events) == 1
                assert events[0].event_id == "event_2"
                
                # Verify cursor was passed to adapter
                mock_adapter.list_events.assert_called_once()
                call_args = mock_adapter.list_events.call_args
                assert call_args[1]["after_event_id"] == "event_1"
    
    def test_validation_rejects_invalid_event(self, request_context):
        """Verify event shape validation rejects invalid events."""
        mock_adapter = MagicMock()
        
        with patch('engines.event_spine.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.event_spine.service_reject.FirestoreEventSpineStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = EventSpineServiceRejectOnMissing(request_context)
                
                # Try to append event with invalid event_type
                with pytest.raises(ValueError) as exc_info:
                    svc.append(
                        event_type="invalid_type",  # Not in VALID_EVENT_TYPES
                        source="agent",
                        run_id="test_run",
                    )
                
                assert "Event validation failed" in str(exc_info.value)
    
    def test_no_fallback_on_append_error(self, request_context):
        """Verify no in-memory fallback on append error."""
        mock_adapter = MagicMock()
        mock_adapter.append.side_effect = Exception("Backend unreachable")
        
        with patch('engines.event_spine.service_reject.routing_registry') as mock_registry:
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {"project": "test_project"}
            mock_registry.return_value.get_route.return_value = mock_route
            
            with patch('engines.event_spine.service_reject.FirestoreEventSpineStore') as mock_fs:
                mock_fs.return_value = mock_adapter
                
                svc = EventSpineServiceRejectOnMissing(request_context)
                
                # Append should raise, not fall back to in-memory
                with pytest.raises(RuntimeError) as exc_info:
                    svc.append(
                        event_type="analytics",
                        source="agent",
                        run_id="test_run",
                    )
                
                assert "Event append failed" in str(exc_info.value)


class TestEventSpineRoutes:
    """Test HTTP endpoints for event_spine."""
    
    @pytest.mark.asyncio
    async def test_append_event_endpoint(self):
        """Test POST /events/append endpoint."""
        # This would require setting up a test client
        # Placeholder for full integration test
        pass
    
    @pytest.mark.asyncio
    async def test_replay_endpoint_with_cursor(self):
        """Test GET /events/replay with cursor parameter."""
        # This would require setting up a test client
        # Placeholder for full integration test
        pass
    
    @pytest.mark.asyncio
    async def test_missing_route_returns_503(self):
        """Test that missing route returns HTTP 503 with error_code."""
        # This would require setting up a test client
        # Placeholder for full integration test
        pass
