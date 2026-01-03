"""Event spine service with routing-based backend resolution (Agent A - A-1).

Routes event_spine resource_kind through routing registry.
Supports Firestore, DynamoDB, Cosmos (cloud); filesystem forbidden in production.
Append-only semantics enforced; identity/causality fields required.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.event_spine.cloud_event_spine_store import (
    SpineEvent,
    FirestoreEventSpineStore,
    DynamoDBEventSpineStore,
    CosmosEventSpineStore,
)

logger = logging.getLogger(__name__)


class EventSpineService:
    """Resolves and uses event_spine backend via routing registry.
    
    Provides append-only event emission with full identity/causality enforcement.
    Single spine for analytics, audit, safety, RL, RLHA, tuning, budget, strategy.
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter()
    
    def _resolve_adapter(self):
        """Resolve event_spine backend via routing registry."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="event_spine",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for event_spine in {self._context.tenant_id}/{self._context.env}. "
                    f"Configure via /routing/routes with backend_type=firestore|dynamodb|cosmos."
                )
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                # Cloud: Firestore
                project = config.get("project")
                return FirestoreEventSpineStore(project=project)
            elif backend_type == "dynamodb":
                # Cloud: DynamoDB
                table_name = config.get("table_name", "event_spine")
                region = config.get("region", "us-west-2")
                return DynamoDBEventSpineStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                # Cloud: Cosmos
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "event_spine")
                return CosmosEventSpineStore(endpoint=endpoint, key=key, database=database)
            else:
                raise RuntimeError(
                    f"Unsupported event_spine backend_type='{backend_type}'. "
                    f"Use 'firestore', 'dynamodb', or 'cosmos'."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
    def emit(
        self,
        event_type: str,
        source: str,
        run_id: str,
        payload: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        surface_id: Optional[str] = None,
        project_id: Optional[str] = None,
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> str:
        """Emit event to spine (append-only).
        
        Required: event_type, source, run_id.
        Identity (tenant_id, mode) derived from context.
        
        Returns: event_id (UUID).
        """
        if not event_type or not source or not run_id:
            raise ValueError("event_type, source, and run_id are required")
        
        event = SpineEvent(
            tenant_id=self._context.tenant_id,
            mode=self._context.mode,
            event_type=event_type,
            source=source,
            run_id=run_id,
            user_id=user_id or self._context.user_id,
            surface_id=surface_id or self._context.surface_id,
            project_id=project_id or self._context.project_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            span_id=span_id,
            payload=payload,
        )
        
        # Append to backend
        self._adapter.append(event, self._context)
        
        logger.debug(
            f"Emitted event {event.event_id} (type={event_type}, run={run_id}) to event_spine"
        )
        return event.event_id
    
    def list_events(
        self,
        run_id: str,
        event_type: Optional[str] = None,
    ) -> List[SpineEvent]:
        """Query spine events for a given run (read-only).
        
        Tenant/mode/user identity enforced server-side.
        """
        return self._adapter.list_events(
            tenant_id=self._context.tenant_id,
            run_id=run_id,
            event_type=event_type,
        )
