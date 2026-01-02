"""Metrics store service with routing-based backend resolution (Lane 3 wiring).

Routes metrics_store resource_kind through routing registry (filesystem default).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.kpi.filesystem_metrics import FileSystemMetricsStore
from engines.routing.registry import MissingRoutingConfig, routing_registry

logger = logging.getLogger(__name__)


class MetricsStoreService:
    """Resolves and uses metrics storage via routing registry.
    
    Provides unified interface for raw metric ingestion and query.
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve metrics_store backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="metrics_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for metrics_store in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=filesystem."
                )
            
            backend_type = (route.backend_type or "").lower()
            
            if backend_type == "filesystem":
                return FileSystemMetricsStore()
            elif backend_type == "firestore":
                # Lane 4: Firestore adapter placeholder (fail-fast NotImplementedError)
                raise NotImplementedError(
                    f"Firestore backend for metrics_store not yet implemented (Lane 4). "
                    f"Use backend_type=filesystem for now."
                )
            else:
                raise RuntimeError(
                    f"Unsupported metrics_store backend_type='{backend_type}'. "
                    f"Use 'filesystem' or 'firestore' (when implemented)."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
    def ingest(
        self, 
        metric_name: str, 
        value: float | int,
        tags: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> None:
        """Append a raw metric data point."""
        self._adapter.ingest(metric_name, value, self._context, tags, source)
    
    def query(
        self, 
        metric_name: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """Query raw metrics, optionally filtered by metric_name."""
        return self._adapter.query(metric_name, self._context)
    
    def get_latest(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get the latest value for a metric."""
        return self._adapter.get_latest(metric_name, self._context)
