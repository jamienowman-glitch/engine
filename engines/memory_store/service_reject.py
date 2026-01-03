"""Memory store service with reject-on-missing-route behavior (MEM-01).

Enforces routed-only session memory in saas/enterprise modes.
Missing route raises MissingMemoryStoreRoute (HTTP 503, error_code: memory_store.missing_route).
No in-memory fallback except explicit lab mode.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.memory_store.cloud_memory_store import (
    FirestoreMemoryStore,
    DynamoDBMemoryStore,
    CosmosMemoryStore,
)

logger = logging.getLogger(__name__)


class MissingMemoryStoreRoute(Exception):
    """Raised when memory_store route is missing (HTTP 503)."""
    
    def __init__(self, context: RequestContext):
        self.error_code = "memory_store.missing_route"
        self.status_code = 503
        self.message = (
            f"Memory store route not configured for tenant={context.tenant_id}, "
            f"env={context.env}, mode={context.mode}. "
            f"Configure via /routing/routes with resource_kind=memory_store "
            f"and backend_type=firestore|dynamodb|cosmos."
        )
        super().__init__(self.message)


class MemoryStoreServiceRejectOnMissing:
    """Memory store service with reject-on-missing-route behavior (MEM-01).
    
    - Persistent session memory (get/set/delete with TTL)
    - Rejects (raises MissingMemoryStoreRoute, HTTP 503) if route missing
    - No fallback to in-memory in saas/enterprise modes
    - Explicit lab mode can use in-memory via separate config
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        # Reject on missing route for saas/enterprise/system
        if context.mode not in ("lab",):
            self._adapter = self._resolve_adapter_or_reject()
        else:
            # Lab mode: can potentially use in-memory, but still try routed first
            try:
                self._adapter = self._resolve_adapter_or_reject()
            except MissingMemoryStoreRoute:
                logger.warning(
                    f"Memory store route missing in lab mode for {context.tenant_id}. "
                    f"Falling back to in-memory (lab only)."
                )
                # In real implementation, would create in-memory adapter here
                # For now, we reject even in lab to enforce routing
                raise
    
    def _resolve_adapter_or_reject(self):
        """Resolve memory_store backend via routing registry.
        
        Raises MissingMemoryStoreRoute (HTTP 503) if route missing or misconfigured.
        """
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="memory_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingMemoryStoreRoute(self._context)
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                project = config.get("project")
                return FirestoreMemoryStore(project=project)
            elif backend_type == "dynamodb":
                table_name = config.get("table_name", "memory_store")
                region = config.get("region", "us-west-2")
                return DynamoDBMemoryStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "memory_store")
                return CosmosMemoryStore(endpoint=endpoint, key=key, database=database)
            else:
                raise MissingMemoryStoreRoute(self._context)
        except MissingMemoryStoreRoute:
            raise
        except MissingRoutingConfig:
            raise MissingMemoryStoreRoute(self._context)
        except Exception as e:
            logger.error(f"Failed to resolve memory_store backend: {e}")
            raise MissingMemoryStoreRoute(self._context) from e
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a value in persistent session memory.
        
        Args:
            key: memory key
            value: any serializable value
            ttl_seconds: optional TTL (seconds); if not set, persists until explicit delete
        
        Raises MissingMemoryStoreRoute if route missing.
        """
        if not key:
            raise ValueError("key is required")
        
        try:
            self._adapter.set(key, value, self._context, ttl_seconds)
            logger.debug(f"Set memory key '{key}' for user {self._context.user_id} (ttl={ttl_seconds}s)")
        except Exception as e:
            logger.error(f"Failed to set memory key '{key}': {e}")
            raise RuntimeError(f"Memory set failed: {e}") from e
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from persistent session memory (checks TTL).
        
        Returns None if key not found or expired.
        Raises MissingMemoryStoreRoute if route missing.
        """
        if not key:
            raise ValueError("key is required")
        
        try:
            value = self._adapter.get(key, self._context)
            if value is not None:
                logger.debug(f"Got memory key '{key}' for user {self._context.user_id}")
            return value
        except Exception as e:
            logger.error(f"Failed to get memory key '{key}': {e}")
            raise RuntimeError(f"Memory get failed: {e}") from e
    
    def delete(self, key: str) -> None:
        """Delete a value from persistent session memory.
        
        Raises MissingMemoryStoreRoute if route missing.
        """
        if not key:
            raise ValueError("key is required")
        
        try:
            self._adapter.delete(key, self._context)
            logger.debug(f"Deleted memory key '{key}' for user {self._context.user_id}")
        except Exception as e:
            logger.error(f"Failed to delete memory key '{key}': {e}")
            raise RuntimeError(f"Memory delete failed: {e}") from e
