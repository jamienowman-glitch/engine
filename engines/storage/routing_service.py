"""Tabular store service with routing-based backend resolution (Lane 3 wiring).

Routes tabular_store resource_kind through routing registry (filesystem default).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.storage.filesystem_tabular import FileSystemTabularStore

logger = logging.getLogger(__name__)


class TabularStoreService:
    """Resolves and uses tabular storage via routing registry.
    
    Provides unified key/value interface for policies and hard facts.
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve tabular_store backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="tabular_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for tabular_store in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=filesystem."
                )
            
            backend_type = (route.backend_type or "").lower()
            
            if backend_type == "filesystem":
                return FileSystemTabularStore()
            else:
                raise RuntimeError(
                    f"Unsupported tabular_store backend_type='{backend_type}'. "
                    f"Use 'filesystem'."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
    def upsert(
        self, 
        table_name: str, 
        key: str, 
        data: Dict[str, Any],
    ) -> None:
        """Upsert a record (update or insert)."""
        self._adapter.upsert(table_name, key, data, self._context)
    
    def get(
        self, 
        table_name: str, 
        key: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a record by key."""
        return self._adapter.get(table_name, key, self._context)
    
    def list_by_prefix(
        self, 
        table_name: str, 
        key_prefix: str,
    ) -> list[Dict[str, Any]]:
        """List records with keys matching prefix."""
        return self._adapter.list_by_prefix(table_name, key_prefix, self._context)
    
    def delete(
        self, 
        table_name: str, 
        key: str,
    ) -> None:
        """Delete a record by key."""
        self._adapter.delete(table_name, key, self._context)
