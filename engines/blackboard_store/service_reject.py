"""BB-01: Blackboard Store Routing-Only Enforcement (Reject on Missing Route).

Enforces blackboard_store to be routing-only:
- Versioned writes with optimistic concurrency
- Reject (HTTP 503) if route missing
- No in-memory fallback in saas/enterprise
- Lab mode exception: warn-only if route missing
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

from engines.common.identity import RequestContext
from engines.routing.registry import routing_registry, MissingRoutingConfig
from engines.blackboard_store.cloud_blackboard_store import (
    FirestoreBlackboardStore,
    DynamoDBBlackboardStore,
    CosmosBlackboardStore,
    VersionConflictError,
)

logger = logging.getLogger(__name__)


@dataclass
class MissingBlackboardStoreRoute(Exception):
    """Raised when blackboard_store route is not configured.
    
    Signals HTTP 503 (service unavailable) to client.
    """
    error_code: str = "blackboard_store.missing_route"
    status_code: int = 503
    message: str = ""
    
    def __str__(self):
        return self.message


class BlackboardStoreServiceRejectOnMissing:
    """Blackboard store with routing-only enforcement.
    
    Features:
    - Versioned writes with optimistic concurrency (expected_version)
    - Rejects (HTTP 503) if route not configured
    - No in-memory fallback
    - Lab mode special case: warn-only if route missing
    
    Usage:
        svc = BlackboardStoreServiceRejectOnMissing(request_context)
        
        # Write with versioning
        svc.write(
            key="strategy_state",
            value={"mode": "active"},
            expected_version=42
        )  # Raises VersionConflictError if version mismatch
        
        # Read (returns {value, version, created_by, created_at, updated_by, updated_at})
        result = svc.read(key="strategy_state")
        
        # List all keys in this blackboard
        keys = svc.list_keys(run_id="run_123")
    """
    
    def __init__(self, context: RequestContext):
        """Initialize with routing registry lookup.
        
        Raises:
            MissingBlackboardStoreRoute: If route not found (saas/enterprise/system modes)
            RuntimeError: If adapter creation fails
        """
        self._context = context
        self._adapter = self._resolve_adapter_or_reject()
    
    def _resolve_adapter_or_reject(self):
        """Resolve backend adapter from routing registry.
        
        Raises MissingBlackboardStoreRoute if route missing in production modes.
        Lab mode: warns if missing, attempts to continue (debug tolerance).
        
        Returns:
            CloudBlackboardStore adapter (Firestore/DynamoDB/Cosmos)
        
        Raises:
            MissingBlackboardStoreRoute: Missing route in saas/enterprise/system
            RuntimeError: Adapter creation failed
        """
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="blackboard_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
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
                raise MissingBlackboardStoreRoute(message=message)
        
        if route is None:
            message = (
                f"No blackboard_store route configured for tenant={self._context.tenant_id}, "
                f"env={self._context.env}, mode={self._context.mode}. "
                f"Configure via /routing/routes with backend_type (firestore|dynamodb|cosmos)."
            )
            
            if self._context.mode == "lab":
                # Lab mode: warn but continue (debug tolerance)
                logger.warning(f"[LAB MODE] Blackboard route missing: {message}")
                return None  # Will be handled in individual methods
            else:
                # Production: reject hard
                raise MissingBlackboardStoreRoute(message=message)
        
        # Instantiate correct backend
        try:
            if route.backend_type == "firestore":
                return FirestoreBlackboardStore(
                    tenant_id=self._context.tenant_id,
                    config=route.config,
                )
            elif route.backend_type == "dynamodb":
                return DynamoDBBlackboardStore(
                    tenant_id=self._context.tenant_id,
                    config=route.config,
                )
            elif route.backend_type == "cosmos":
                return CosmosBlackboardStore(
                    tenant_id=self._context.tenant_id,
                    config=route.config,
                )
            else:
                raise RuntimeError(
                    f"Unknown backend_type for blackboard_store: {route.backend_type}"
                )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Blackboard adapter initialization failed: {str(e)}")
    
    def write(
        self,
        key: str,
        value: Dict[str, Any],
        expected_version: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write versioned value to blackboard.
        
        Args:
            key: Unique identifier within this run
            value: Dict to store (must be JSON-serializable)
            expected_version: Expected current version; if mismatch, raises VersionConflictError
            run_id: Run identifier; defaults to from context if available
        
        Returns:
            {key, value, version, created_by, created_at, updated_by, updated_at}
        
        Raises:
            VersionConflictError: Version mismatch (optimistic concurrency)
            RuntimeError: Backend write failed
            MissingBlackboardStoreRoute: Route missing in production mode
        """
        if self._adapter is None:
            raise RuntimeError(
                "Blackboard write failed: route not configured and mode is not lab"
            )
        
        if run_id is None:
            raise ValueError("run_id is required")
        
        try:
            result = self._adapter.write(
                key=key,
                value=value,
                context=self._context,
                run_id=run_id,
                expected_version=expected_version,
            )
            return result
        except VersionConflictError:
            raise
        except Exception as e:
            raise RuntimeError(f"Blackboard write failed: {str(e)}")
    
    def read(self, key: str, version: Optional[int] = None, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Read versioned value from blackboard.
        
        Args:
            key: Unique identifier within this run
            version: Specific version to read; if None, reads latest
            run_id: Run identifier; defaults to from context if available
        
        Returns:
            {key, value, version, created_by, created_at, updated_by, updated_at}
            Returns None if key not found.
        
        Raises:
            RuntimeError: Backend read failed
            MissingBlackboardStoreRoute: Route missing in production mode
        """
        if self._adapter is None:
            raise RuntimeError(
                "Blackboard read failed: route not configured and mode is not lab"
            )
        
        if run_id is None:
            raise ValueError("run_id is required")
        
        try:
            result = self._adapter.read(
                key=key,
                context=self._context,
                run_id=run_id,
                version=version,
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Blackboard read failed: {str(e)}")
    
    def list_keys(self, run_id: str) -> list[str]:
        """List all keys in this blackboard.
        
        Args:
            run_id: The run identifier
        
        Returns:
            List of key names
        
        Raises:
            RuntimeError: Backend list failed
            MissingBlackboardStoreRoute: Route missing in production mode
        """
        if self._adapter is None:
            raise RuntimeError(
                "Blackboard list_keys failed: route not configured and mode is not lab"
            )
        
        try:
            result = self._adapter.list_keys(
                context=self._context,
                run_id=run_id,
            )
            return result
        except Exception as e:
            raise RuntimeError(f"Blackboard list_keys failed: {str(e)}")
