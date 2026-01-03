"""Tabular store service with routing-based backend resolution (Builder A).

Routes tabular_store resource_kind through routing registry.
Supports filesystem (lab), Firestore, DynamoDB, Cosmos (cloud).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.storage.filesystem_tabular import FileSystemTabularStore
from engines.storage.cloud_tabular_store import (
    FirestoreTabularStore,
    DynamoDBTabularStore,
    CosmosTabularStore,
)

logger = logging.getLogger(__name__)


class TabularStoreService:
    """Resolves and uses tabular storage via routing registry.
    
    Provides unified key/value interface for policies and hard facts.
    """
    
    def __init__(self, context: RequestContext, resource_kind: str = "tabular_store") -> None:
        self._context = context
        self._resource_kind = resource_kind
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve tabular_store backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind=self._resource_kind,
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                logger.warning(
                    "No route configured for %s in %s/%s. Configure via /routing/routes with backend_type=filesystem|firestore|dynamodb|cosmos.",
                    self._resource_kind,
                    self._context.tenant_id,
                    self._context.env,
                )
                raise MissingRoutingConfig(
                    f"No route configured for {self._resource_kind} in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=filesystem|firestore|dynamodb|cosmos."
                )
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "filesystem":
                # Lab-only filesystem
                if self._context.mode not in ("lab",):
                    raise RuntimeError(
                        f"Filesystem backend for tabular_store not allowed in mode={self._context.mode}. "
                        f"Use firestore, dynamodb, or cosmos."
                    )
                return FileSystemTabularStore()
            elif backend_type == "firestore":
                # Cloud: Firestore (Builder A real implementation)
                project = config.get("project")
                return FirestoreTabularStore(project=project)
            elif backend_type == "dynamodb":
                # Cloud: DynamoDB (Builder A real implementation)
                table_name = config.get("table_name")
                region = config.get("region", "us-west-2")
                return DynamoDBTabularStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                # Cloud: Cosmos (Builder A real implementation)
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "tabular_store")
                return CosmosTabularStore(endpoint=endpoint, key=key, database=database)
            else:
                raise RuntimeError(
                    f"Unsupported tabular_store backend_type='{backend_type}'. "
                    f"Use 'filesystem' (lab), 'firestore', 'dynamodb', or 'cosmos'."
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
