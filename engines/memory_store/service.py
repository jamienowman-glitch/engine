"""Memory store service with routing-based backend resolution (Agent A - A-3).

Routes memory_store resource_kind through routing registry.
Provides persistent session memory with configurable TTL.
Scope: tenant / mode / project / user / session.
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


class MemoryStoreService:
    """Resolves and uses memory_store backend via routing registry.
    
    Provides persistent session memory (conversational continuity across hosts/restarts).
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve memory_store backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="memory_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for memory_store in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=firestore|dynamodb|cosmos."
                )
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                # Cloud: Firestore
                project = config.get("project")
                return FirestoreMemoryStore(project=project)
            elif backend_type == "dynamodb":
                # Cloud: DynamoDB
                table_name = config.get("table_name", "memory_store")
                region = config.get("region", "us-west-2")
                return DynamoDBMemoryStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                # Cloud: Cosmos
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "memory_store")
                return CosmosMemoryStore(endpoint=endpoint, key=key, database=database)
            else:
                raise RuntimeError(
                    f"Unsupported memory_store backend_type='{backend_type}'. "
                    f"Use 'firestore', 'dynamodb', or 'cosmos'."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
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
            ttl_seconds: optional TTL; if not set, persists until explicit delete
        """
        self._adapter.set(key, value, self._context, ttl_seconds)
        logger.debug(f"Set memory key '{key}' (ttl={ttl_seconds}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from persistent session memory (checks TTL).
        
        Returns None if key not found or expired.
        """
        return self._adapter.get(key, self._context)
    
    def delete(self, key: str) -> None:
        """Delete a value from persistent session memory."""
        self._adapter.delete(key, self._context)
        logger.debug(f"Deleted memory key '{key}'")
