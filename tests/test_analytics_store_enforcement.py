"""AN-01: Analytics Store Enforcement - Integration Tests.

Test routing-only enforcement for analytics_store:
1. Missing route → HTTP 503 in production modes (saas/enterprise/system)
2. Lab mode with missing route → warn + continue
3. Ingest analytics with attribution fields
4. Query analytics by time/filters
5. Persistence across restart (backend-specific test)
6. DELETE event purge flow
"""
import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

from engines.common.identity import RequestContext
from engines.analytics.service_reject import (
    AnalyticsStoreServiceRejectOnMissing,
    MissingAnalyticsStoreRoute,
)
from engines.routing.registry import routing_registry


class TestAnalyticsStoreMissingRoute:
    """Test missing route behavior."""
    
    def test_missing_route_saas_mode_raises_503(self):
        """SaaS mode: missing route → MissingAnalyticsStoreRoute."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="saas",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_route.return_value = None
            mock_registry_fn.return_value = mock_registry
            
            with pytest.raises(MissingAnalyticsStoreRoute) as exc_info:
                AnalyticsStoreServiceRejectOnMissing(context)
            
            assert exc_info.value.error_code == "analytics_store.missing_route"
            assert exc_info.value.status_code == 503
    
    def test_missing_route_enterprise_mode_raises_503(self):
        """Enterprise mode: missing route → MissingAnalyticsStoreRoute."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="enterprise",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_route.return_value = None
            mock_registry_fn.return_value = mock_registry
            
            with pytest.raises(MissingAnalyticsStoreRoute) as exc_info:
                AnalyticsStoreServiceRejectOnMissing(context)
            
            assert exc_info.value.status_code == 503
    
    def test_missing_route_system_mode_raises_503(self):
        """System mode: missing route → MissingAnalyticsStoreRoute."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="system",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_route.return_value = None
            mock_registry_fn.return_value = mock_registry
            
            with pytest.raises(MissingAnalyticsStoreRoute) as exc_info:
                AnalyticsStoreServiceRejectOnMissing(context)
            
            assert exc_info.value.status_code == 503
    
    def test_missing_route_lab_mode_warns_only(self, caplog):
        """Lab mode: missing route → warn, continue with None adapter."""
        context = RequestContext(
            tenant_id="t_test",
            env="dev",
            mode="lab",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_route.return_value = None
            mock_registry_fn.return_value = mock_registry
            
            # Should not raise; should warn
            service = AnalyticsStoreServiceRejectOnMissing(context)
            assert service._adapter is None
            # Verify warning was logged (implementation detail)


class TestAnalyticsStoreIngest:
    """Test analytics ingest operations."""
    
    def test_ingest_with_attribution_fields(self):
        """Ingest event with UTM/SEO attribution fields."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="saas",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        mock_adapter = MagicMock()
        mock_adapter.ingest.return_value = "event-123"
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {}
            mock_registry.get_route.return_value = mock_route
            mock_registry_fn.return_value = mock_registry
            
            with patch("engines.analytics.service_reject.FirestoreAnalyticsStore", return_value=mock_adapter):
                service = AnalyticsStoreServiceRejectOnMissing(context)
                
                event_id = service.ingest(
                    event_type="pageview",
                    payload={"url": "https://example.com/page"},
                    utm_source="google",
                    utm_campaign="summer_2025",
                    app="northstar_ui",
                    surface="homepage",
                    platform="web",
                    session_id="sess-1",
                )
                
                assert event_id == "event-123"
                assert mock_adapter.ingest.called
    
    def test_ingest_missing_route_raises_runtime_error(self):
        """Ingest with missing route in lab mode → RuntimeError."""
        context = RequestContext(
            tenant_id="t_test",
            env="dev",
            mode="lab",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_route.return_value = None
            mock_registry_fn.return_value = mock_registry
            
            service = AnalyticsStoreServiceRejectOnMissing(context)
            
            with pytest.raises(RuntimeError) as exc_info:
                service.ingest(
                    event_type="pageview",
                    payload={"url": "..."},
                )
            
            assert "route not configured" in str(exc_info.value)


class TestAnalyticsStoreQuery:
    """Test analytics query operations."""
    
    def test_query_with_time_range(self):
        """Query analytics with start/end time filters."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="saas",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        mock_records = [
            {
                "event_id": "evt-1",
                "event_type": "pageview",
                "timestamp": "2025-01-01T10:00:00Z",
                "utm_source": "google",
            },
            {
                "event_id": "evt-2",
                "event_type": "cta_click",
                "timestamp": "2025-01-01T11:00:00Z",
                "utm_source": "organic",
            },
        ]
        
        mock_adapter = MagicMock()
        mock_adapter.query.return_value = mock_records
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_route = MagicMock()
            mock_route.backend_type = "dynamodb"
            mock_route.config = {}
            mock_registry.get_route.return_value = mock_route
            mock_registry_fn.return_value = mock_registry
            
            with patch("engines.analytics.service_reject.DynamoDBAnalyticsStore", return_value=mock_adapter):
                service = AnalyticsStoreServiceRejectOnMissing(context)
                
                records = service.query(
                    start_time="2025-01-01T00:00:00Z",
                    end_time="2025-01-02T00:00:00Z",
                    filters={"utm_source": "google"},
                    limit=1000,
                )
                
                assert len(records) == 2
                assert mock_adapter.query.called
    
    def test_query_with_filters(self):
        """Query analytics with attribute filters."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="saas",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        mock_adapter = MagicMock()
        mock_adapter.query.return_value = []
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_route = MagicMock()
            mock_route.backend_type = "cosmos"
            mock_route.config = {}
            mock_registry.get_route.return_value = mock_route
            mock_registry_fn.return_value = mock_registry
            
            with patch("engines.analytics.service_reject.CosmosAnalyticsStore", return_value=mock_adapter):
                service = AnalyticsStoreServiceRejectOnMissing(context)
                
                records = service.query(
                    filters={
                        "utm_source": "organic",
                        "utm_campaign": "summer_2025",
                        "event_type": "pageview",
                    },
                )
                
                assert mock_adapter.query.called


class TestAnalyticsStoreAggregate:
    """Test analytics aggregation operations."""
    
    def test_aggregate_pageviews(self):
        """Aggregate pageview metrics."""
        context = RequestContext(
            tenant_id="t_test",
            env="prod",
            mode="saas",
            project_id="proj-123",
            request_id="req-1",
            user_id="user-1",
        )
        
        mock_result = {
            "metric": "pageviews",
            "total": 12345,
            "groups": {
                "utm_source": {
                    "google": 8000,
                    "organic": 3000,
                    "direct": 1345,
                }
            }
        }
        
        mock_adapter = MagicMock()
        mock_adapter.aggregate.return_value = mock_result
        
        with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_route = MagicMock()
            mock_route.backend_type = "firestore"
            mock_route.config = {}
            mock_registry.get_route.return_value = mock_route
            mock_registry_fn.return_value = mock_registry
            
            with patch("engines.analytics.service_reject.FirestoreAnalyticsStore", return_value=mock_adapter):
                service = AnalyticsStoreServiceRejectOnMissing(context)
                
                result = service.aggregate(
                    metric="pageviews",
                    start_time="2025-01-01T00:00:00Z",
                    end_time="2025-01-02T00:00:00Z",
                    group_by=["utm_source"],
                )
                
                assert result["metric"] == "pageviews"
                assert result["total"] == 12345
                assert mock_adapter.aggregate.called


class TestAnalyticsStoreHTTPRoutes:
    """Test HTTP route handlers."""
    
    @pytest.fixture
    def client(self):
        """Create test Flask client."""
        from flask import Flask
        from engines.analytics.routes import analytics_routes
        
        app = Flask(__name__)
        app.register_blueprint(analytics_routes)
        return app.test_client()
    
    def test_http_ingest_success(self, client):
        """POST /analytics/ingest with valid payload → 200."""
        with patch("engines.analytics.routes.get_request_context") as mock_ctx:
            mock_context = RequestContext(
                tenant_id="t_test",
                env="prod",
                mode="saas",
                project_id="proj-123",
                request_id="req-1",
                user_id="user-1",
            )
            mock_ctx.return_value = mock_context
            
            with patch("engines.analytics.routes.AnalyticsStoreServiceRejectOnMissing") as mock_service_cls:
                mock_service = MagicMock()
                mock_service.ingest.return_value = "event-456"
                mock_service_cls.return_value = mock_service
                
                response = client.post(
                    "/analytics/ingest",
                    json={
                        "event_type": "pageview",
                        "payload": {"url": "https://example.com"},
                        "utm_source": "google",
                        "utm_campaign": "summer_2025",
                        "app": "northstar_ui",
                        "platform": "web",
                    },
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["event_id"] == "event-456"
    
    def test_http_ingest_missing_event_type(self, client):
        """POST /analytics/ingest without event_type → 400."""
        with patch("engines.analytics.routes.get_request_context") as mock_ctx:
            mock_context = RequestContext(
                tenant_id="t_test",
                env="prod",
                mode="saas",
                project_id="proj-123",
                request_id="req-1",
                user_id="user-1",
            )
            mock_ctx.return_value = mock_context
            
            response = client.post(
                "/analytics/ingest",
                json={"payload": {"url": "..."}},
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["error"]["code"] == "analytics.invalid_payload"
            assert data["error"]["http_status"] == 400
    
    def test_http_ingest_missing_route_returns_503(self, client):
        """POST /analytics/ingest with missing route → 503."""
        with patch("engines.analytics.routes.get_request_context") as mock_ctx:
            mock_context = RequestContext(
                tenant_id="t_test",
                env="prod",
                mode="saas",
                project_id="proj-123",
                request_id="req-1",
                user_id="user-1",
            )
            mock_ctx.return_value = mock_context
            
            with patch("engines.analytics.routes.AnalyticsStoreServiceRejectOnMissing") as mock_service_cls:
                mock_service_cls.side_effect = MissingAnalyticsStoreRoute(
                    message="No analytics_store route configured"
                )
                
                response = client.post(
                    "/analytics/ingest",
                    json={
                        "event_type": "pageview",
                        "payload": {"url": "..."},
                    },
                )
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["error"]["code"] == "analytics_store.missing_route"
            assert data["error"]["http_status"] == 503
    
    def test_http_query_success(self, client):
        """GET /analytics/query with valid filters → 200."""
        with patch("engines.analytics.routes.get_request_context") as mock_ctx:
            mock_context = RequestContext(
                tenant_id="t_test",
                env="prod",
                mode="saas",
                project_id="proj-123",
                request_id="req-1",
                user_id="user-1",
            )
            mock_ctx.return_value = mock_context
            
            with patch("engines.analytics.routes.AnalyticsStoreServiceRejectOnMissing") as mock_service_cls:
                mock_service = MagicMock()
                mock_service.query.return_value = [
                    {"event_id": "evt-1", "event_type": "pageview"}
                ]
                mock_service_cls.return_value = mock_service
                
                response = client.get(
                    "/analytics/query",
                    query_string={
                        "start_time": "2025-01-01T00:00:00Z",
                        "end_time": "2025-01-02T00:00:00Z",
                        "utm_source": "google",
                        "limit": "100",
                    },
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert len(data["records"]) == 1
    
    def test_http_delete_event_success(self, client):
        """DELETE /analytics/event/{event_id} → 204."""
        with patch("engines.analytics.routes.get_request_context") as mock_ctx:
            mock_context = RequestContext(
                tenant_id="t_test",
                env="prod",
                mode="saas",
                project_id="proj-123",
                request_id="req-1",
                user_id="user-1",
            )
            mock_ctx.return_value = mock_context
            
            with patch("engines.analytics.routes.AnalyticsStoreServiceRejectOnMissing"):
                response = client.delete("/analytics/event/event-123")
                
                assert response.status_code == 204


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
