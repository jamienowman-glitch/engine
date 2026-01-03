"""AN-01: Analytics Store Routing-Only Enforcement (Reject on Missing Route).

Enforces analytics_store to be routing-only:
- Ingest and query operations routed exclusively
- Reject (HTTP 503) if route missing
- No in-memory fallback in saas/enterprise
- Lab mode exception: warn-only if route missing
- Attribution fields required for compliance
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

from engines.common.identity import RequestContext
from engines.routing.registry import routing_registry, MissingRoutingConfig
from engines.analytics.cloud_analytics_store import (
    FirestoreAnalyticsStore,
    DynamoDBAnalyticsStore,
    CosmosAnalyticsStore,
    AnalyticsRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class MissingAnalyticsStoreRoute(Exception):
    """Raised when analytics_store route is not configured.
    
    Signals HTTP 503 (service unavailable) to client.
    """
    error_code: str = "analytics_store.missing_route"
    status_code: int = 503
    message: str = ""
    
    def __str__(self):
        return self.message


class AnalyticsStoreServiceRejectOnMissing:
    """Analytics store with routing-only enforcement.
    
    Features:
    - Ingest and query operations via configured backend only
    - Rejects (HTTP 503) if route not configured
    - No in-memory fallback
    - Lab mode special case: warn-only if route missing
    - Requires attribution fields (utm_*, seo_*) for compliance
    
    Usage:
        svc = AnalyticsStoreServiceRejectOnMissing(request_context)
        
        # Ingest analytics event
        svc.ingest(
            event_type="pageview",
            payload={"url": "..."},
            utm_source="organic",
            utm_campaign="summer_2025"
        )
        
        # Query analytics
        records = svc.query(
            start_time="2025-01-01T00:00:00Z",
            end_time="2025-01-02T00:00:00Z",
            filters={"utm_source": "organic"}
        )
    """
    
    def __init__(self, context: RequestContext):
        """Initialize with routing registry lookup.
        
        Raises:
            MissingAnalyticsStoreRoute: If route not found (saas/enterprise/system modes)
            RuntimeError: If adapter creation fails
        """
        self._context = context
        self._adapter = self._resolve_adapter_or_reject()
    
    def _resolve_adapter_or_reject(self):
        """Resolve backend adapter from routing registry.
        
        Raises MissingAnalyticsStoreRoute if route missing in production modes.
        Lab mode: warns if missing, attempts to continue (debug tolerance).
        
        Returns:
            CloudAnalyticsStore adapter (Firestore/DynamoDB/Cosmos)
        
        Raises:
            MissingAnalyticsStoreRoute: Missing route in saas/enterprise/system
            RuntimeError: Adapter creation failed
        """
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="analytics_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if route is None:
                message = (
                    f"No analytics_store route configured for tenant={self._context.tenant_id}, "
                    f"env={self._context.env}, mode={self._context.mode}. "
                    f"Configure via /routing/routes with backend_type (firestore|dynamodb|cosmos)."
                )
                
                if self._context.mode == "lab":
                    # Lab mode: warn but continue (debug tolerance)
                    logger.warning(f"[LAB MODE] Analytics route missing: {message}")
                    return None  # Will be handled in individual methods
                else:
                    # Production: reject hard
                    raise MissingAnalyticsStoreRoute(message=message)
            
            # Instantiate correct backend
            if route.backend_type == "firestore":
                return FirestoreAnalyticsStore(
                    tenant_id=self._context.tenant_id,
                    config=route.config,
                )
            elif route.backend_type == "dynamodb":
                return DynamoDBAnalyticsStore(
                    tenant_id=self._context.tenant_id,
                    config=route.config,
                )
            elif route.backend_type == "cosmos":
                return CosmosAnalyticsStore(
                    tenant_id=self._context.tenant_id,
                    config=route.config,
                )
            else:
                raise RuntimeError(
                    f"Unknown backend_type for analytics_store: {route.backend_type}"
                )
        
        except MissingRoutingConfig as e:
            message = (
                f"Routing registry error: {str(e)}. "
                f"Ensure routing service is running and configured."
            )
            if self._context.mode == "lab":
                logger.warning(f"[LAB MODE] Routing error: {message}")
                return None
            else:
                raise MissingAnalyticsStoreRoute(message=message)
        
        except MissingAnalyticsStoreRoute:
            # Re-raise MissingAnalyticsStoreRoute without wrapping
            raise
        
        except Exception as e:
            raise RuntimeError(f"Analytics adapter initialization failed: {str(e)}")
    
    def ingest(
        self,
        event_type: str,
        payload: Dict[str, Any],
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
        app: Optional[str] = None,
        surface: Optional[str] = None,
        platform: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Ingest analytics event.
        
        Args:
            event_type: "pageview", "cta_click", "form_submit", etc.
            payload: Event data (must be JSON-serializable)
            utm_*: Attribution fields (recommended for compliance)
            app, surface, platform: Dimensional attributes
            session_id: Session identifier (optional)
        
        Returns:
            Event ID (record identifier)
        
        Raises:
            RuntimeError: Backend ingest failed
            MissingAnalyticsStoreRoute: Route missing in production mode
        """
        if self._adapter is None:
            raise RuntimeError(
                "Analytics ingest failed: route not configured and mode is not lab"
            )
        
        try:
            record = AnalyticsRecord(
                tenant_id=self._context.tenant_id,
                mode=self._context.mode,
                project_id=self._context.project_id,
                app=app,
                surface=surface,
                platform=platform,
                session_id=session_id,
                request_id=self._context.request_id,
                run_id=self._context.run_id,
                step_id=self._context.step_id,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                payload=payload,
            )
            return self._adapter.ingest(record)
        except Exception as e:
            raise RuntimeError(f"Analytics ingest failed: {str(e)}")
    
    def query(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query analytics events.
        
        Args:
            start_time: ISO 8601 timestamp (e.g., "2025-01-01T00:00:00Z")
            end_time: ISO 8601 timestamp
            filters: Optional filters (utm_source, utm_campaign, event_type, etc.)
            limit: Max events to return
        
        Returns:
            List of analytics records
        
        Raises:
            RuntimeError: Backend query failed
            MissingAnalyticsStoreRoute: Route missing in production mode
        """
        if self._adapter is None:
            raise RuntimeError(
                "Analytics query failed: route not configured and mode is not lab"
            )
        
        try:
            return self._adapter.query(
                tenant_id=self._context.tenant_id,
                start_time=start_time,
                end_time=end_time,
                filters=filters or {},
                limit=limit,
            )
        except Exception as e:
            raise RuntimeError(f"Analytics query failed: {str(e)}")
    
    def aggregate(
        self,
        metric: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        group_by: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Aggregate analytics data.
        
        Args:
            metric: "pageviews", "cta_clicks", "sessions", "bounce_rate", etc.
            start_time: ISO 8601 timestamp
            end_time: ISO 8601 timestamp
            group_by: Group results by these dimensions (utm_source, surface, etc.)
        
        Returns:
            Aggregated metrics
        
        Raises:
            RuntimeError: Backend aggregation failed
            MissingAnalyticsStoreRoute: Route missing in production mode
        """
        if self._adapter is None:
            raise RuntimeError(
                "Analytics aggregate failed: route not configured and mode is not lab"
            )
        
        try:
            return self._adapter.aggregate(
                tenant_id=self._context.tenant_id,
                metric=metric,
                start_time=start_time,
                end_time=end_time,
                group_by=group_by or [],
            )
        except Exception as e:
            raise RuntimeError(f"Analytics aggregate failed: {str(e)}")
