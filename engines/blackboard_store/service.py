"""Blackboard store service with routing-based backend resolution (Agent A - A-4).

Routes blackboard_store resource_kind through routing registry.
Provides persistent shared coordination state with versioned writes and optimistic concurrency.
Scope: tenant / mode / project / run.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.blackboard_store.cloud_blackboard_store import (
    FirestoreBlackboardStore,
    DynamoDBBlackboardStore,
    CosmosBlackboardStore,
    VersionConflictError,
)

logger = logging.getLogger(__name__)


class BlackboardStoreService:
    """Resolves and uses blackboard_store backend via routing registry.
    
    Provides persistent shared state for agent coordination with versioning.
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve blackboard_store backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="blackboard_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for blackboard_store in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=firestore|dynamodb|cosmos."
                )
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                # Cloud: Firestore
                project = config.get("project")
                return FirestoreBlackboardStore(project=project)
            elif backend_type == "dynamodb":
                # Cloud: DynamoDB
                table_name = config.get("table_name", "blackboard_store")
                region = config.get("region", "us-west-2")
                return DynamoDBBlackboardStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                # Cloud: Cosmos
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "blackboard_store")
                return CosmosBlackboardStore(endpoint=endpoint, key=key, database=database)
            else:
                raise RuntimeError(
                    f"Unsupported blackboard_store backend_type='{backend_type}'. "
                    f"Use 'firestore', 'dynamodb', or 'cosmos'."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
    def write(
        self,
        key: str,
        value: Any,
        run_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Write a value to shared blackboard with optimistic concurrency.
        
        Args:
            key: blackboard key
            value: any serializable value
            run_id: provenance identifier
            expected_version: if provided, only write if current version matches
        
        Returns: dict with key, value, version, created_by, created_at, updated_by, updated_at
        Raises: VersionConflictError if version mismatch (concurrent update)
        """
        try:
            return self._adapter.write(key, value, self._context, run_id, expected_version)
        except VersionConflictError:
            raise
        except Exception as exc:
            logger.error(f"Blackboard write failed for key '{key}': {exc}")
            raise
    
    def read(
        self,
        key: str,
        run_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read a value from shared blackboard (latest or specific version).
        
        Returns dict with: value, version, created_by, created_at, updated_by, updated_at
        Returns None if not found.
        """
        try:
            return self._adapter.read(key, self._context, run_id, version)
        except Exception as exc:
            logger.error(f"Blackboard read failed for key '{key}': {exc}")
            return None
    
    def list_keys(self, run_id: str) -> List[str]:
        """List all keys in blackboard for a run."""
        try:
            return self._adapter.list_keys(self._context, run_id)
        except Exception as exc:
            logger.error(f"Blackboard list_keys failed for run {run_id}: {exc}")
            return []
