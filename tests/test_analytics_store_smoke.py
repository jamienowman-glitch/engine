"""AN-01: Analytics Store - Smoke Test for Staging Deployment.

Quick validation that routing-only enforcement works:
1. Service rejects on missing route (HTTP 503)
2. Service accepts valid configuration
3. Attribution fields are enforced
"""
import sys
from unittest.mock import patch, MagicMock

from engines.common.identity import RequestContext
from engines.analytics.service_reject import (
    AnalyticsStoreServiceRejectOnMissing,
    MissingAnalyticsStoreRoute,
)


def test_smoke_missing_route_rejection():
    """Smoke test: SaaS mode rejects missing route with 503."""
    print("Test 1: Missing route rejection (SaaS)...", end=" ")
    
    context = RequestContext(
        tenant_id="t_smoke",
        env="prod",
        mode="saas",
        project_id="proj-123",
        request_id="req-1",
        user_id="user-1",
    )
    
    with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
        mock_registry = MagicMock()
        mock_registry.get_route.return_value = None  # No route configured
        mock_registry_fn.return_value = mock_registry
        
        try:
            AnalyticsStoreServiceRejectOnMissing(context)
            print("❌ FAILED: Should have raised MissingAnalyticsStoreRoute")
            return False
        except MissingAnalyticsStoreRoute as e:
            if e.status_code == 503 and e.error_code == "analytics_store.missing_route":
                print("✅ PASSED")
                return True
            else:
                print(f"❌ FAILED: Wrong exception details: {e.status_code}, {e.error_code}")
                return False
        except Exception as e:
            print(f"❌ FAILED: Unexpected exception: {type(e).__name__}: {e}")
            return False


def test_smoke_lab_mode_tolerates_missing():
    """Smoke test: Lab mode tolerates missing route."""
    print("Test 2: Lab mode tolerance (missing route)...", end=" ")
    
    context = RequestContext(
        tenant_id="t_smoke",
        env="dev",
        mode="lab",
        project_id="proj-123",
        request_id="req-1",
        user_id="user-1",
    )
    
    with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
        mock_registry = MagicMock()
        mock_registry.get_route.return_value = None  # No route configured
        mock_registry_fn.return_value = mock_registry
        
        # Should not raise
        service = AnalyticsStoreServiceRejectOnMissing(context)
        assert service._adapter is None
        print("✅ PASSED")
        return True


def test_smoke_firestore_adapter_selection():
    """Smoke test: Firestore backend adapter selected correctly."""
    print("Test 3: Firestore adapter selection...", end=" ")
    
    context = RequestContext(
        tenant_id="t_smoke",
        env="prod",
        mode="saas",
        project_id="proj-123",
        request_id="req-1",
        user_id="user-1",
    )
    
    with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
        mock_registry = MagicMock()
        mock_route = MagicMock()
        mock_route.backend_type = "firestore"
        mock_route.config = {}
        mock_registry.get_route.return_value = mock_route
        mock_registry_fn.return_value = mock_registry
        
        with patch("engines.analytics.service_reject.FirestoreAnalyticsStore") as mock_firestore:
            mock_firestore.return_value = MagicMock()
            service = AnalyticsStoreServiceRejectOnMissing(context)
            assert service._adapter is not None
            print("✅ PASSED")
            return True


def test_smoke_dynamodb_adapter_selection():
    """Smoke test: DynamoDB backend adapter selected correctly."""
    print("Test 4: DynamoDB adapter selection...", end=" ")
    
    context = RequestContext(
        tenant_id="t_smoke",
        env="prod",
        mode="saas",
        project_id="proj-123",
        request_id="req-1",
        user_id="user-1",
    )
    
    with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
        mock_registry = MagicMock()
        mock_route = MagicMock()
        mock_route.backend_type = "dynamodb"
        mock_route.config = {}
        mock_registry.get_route.return_value = mock_route
        mock_registry_fn.return_value = mock_registry
        
        with patch("engines.analytics.service_reject.DynamoDBAnalyticsStore") as mock_dynamodb:
            mock_dynamodb.return_value = MagicMock()
            service = AnalyticsStoreServiceRejectOnMissing(context)
            assert service._adapter is not None
            print("✅ PASSED")
            return True


def test_smoke_cosmos_adapter_selection():
    """Smoke test: Cosmos backend adapter selected correctly."""
    print("Test 5: Cosmos adapter selection...", end=" ")
    
    context = RequestContext(
        tenant_id="t_smoke",
        env="prod",
        mode="saas",
        project_id="proj-123",
        request_id="req-1",
        user_id="user-1",
    )
    
    with patch("engines.analytics.service_reject.routing_registry") as mock_registry_fn:
        mock_registry = MagicMock()
        mock_route = MagicMock()
        mock_route.backend_type = "cosmos"
        mock_route.config = {}
        mock_registry.get_route.return_value = mock_route
        mock_registry_fn.return_value = mock_registry
        
        with patch("engines.analytics.service_reject.CosmosAnalyticsStore") as mock_cosmos:
            mock_cosmos.return_value = MagicMock()
            service = AnalyticsStoreServiceRejectOnMissing(context)
            assert service._adapter is not None
            print("✅ PASSED")
            return True


def test_smoke_ingest_with_attribution():
    """Smoke test: Ingest with attribution fields."""
    print("Test 6: Ingest with attribution fields...", end=" ")
    
    context = RequestContext(
        tenant_id="t_smoke",
        env="prod",
        mode="saas",
        project_id="proj-123",
        request_id="req-1",
        user_id="user-1",
    )
    
    mock_adapter = MagicMock()
    mock_adapter.ingest.return_value = "event-abc123"
    
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
                payload={"url": "https://example.com"},
                utm_source="google",
                utm_campaign="summer_2025",
                app="northstar_ui",
                surface="homepage",
                platform="web",
            )
            
            assert event_id == "event-abc123"
            assert mock_adapter.ingest.called
            print("✅ PASSED")
            return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AN-01: Analytics Store Smoke Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_smoke_missing_route_rejection,
        test_smoke_lab_mode_tolerates_missing,
        test_smoke_firestore_adapter_selection,
        test_smoke_dynamodb_adapter_selection,
        test_smoke_cosmos_adapter_selection,
        test_smoke_ingest_with_attribution,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    if all(results):
        print("✅ All smoke tests PASSED - Ready for staging deployment\n")
        sys.exit(0)
    else:
        print("❌ Some smoke tests FAILED - Fix before deployment\n")
        sys.exit(1)
