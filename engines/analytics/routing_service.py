"""Analytics store routing service (Builder B).

Routes analytics_store via routing registry.
Supports Firestore, DynamoDB, Cosmos backends.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.analytics.cloud_analytics_store import (
    AnalyticsRecord,
    FirestoreAnalyticsStore,
    DynamoDBAnalyticsStore,
    CosmosAnalyticsStore,
)

logger = logging.getLogger(__name__)


class AnalyticsStoreService:
    """Routes and uses analytics store via routing registry."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve analytics_store backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="analytics_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for analytics_store in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=firestore|dynamodb|cosmos."
                )
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                project = config.get("project")
                return FirestoreAnalyticsStore(project=project)
            elif backend_type == "dynamodb":
                table_name = config.get("table_name", "analytics_store")
                region = config.get("region", "us-west-2")
                return DynamoDBAnalyticsStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "analytics_store")
                return CosmosAnalyticsStore(endpoint=endpoint, key=key, database=database)
            else:
                raise RuntimeError(
                    f"Unsupported analytics_store backend_type='{backend_type}'. "
                    f"Use 'firestore', 'dynamodb', or 'cosmos'."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
    def ingest(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        app: Optional[str] = None,
        surface: Optional[str] = None,
        platform: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """Ingest analytics event (GateChain errors persist with status=gatechainerror)."""
        record = AnalyticsRecord(
            tenant_id=tenant_id,
            mode=mode,
            project_id=project_id,
            app=app,
            surface=surface,
            platform=platform,
            session_id=session_id,
            request_id=request_id,
            run_id=run_id,
            step_id=step_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            payload=payload,
            status=status,
            error_message=error_message,
        )
        self._adapter.ingest(record)
    
    def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[AnalyticsRecord]:
        """Query analytics events."""
        return self._adapter.query(self._context.tenant_id, filters=filters, limit=limit)
    
    def query_by_run(self, run_id: str) -> List[AnalyticsRecord]:
        """Query all events for a run."""
        return self._adapter.query_by_run(run_id, self._context.tenant_id)
