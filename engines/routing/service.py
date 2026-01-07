"""Routing control-plane service with audit and stream events."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from engines.common.identity import RequestContext
from engines.logging.audit import emit_audit_event
from engines.realtime.contracts import (
    ActorType,
    EventIds,
    EventMeta,
    EventPriority,
    PersistPolicy,
    RoutingKeys,
    StreamEvent,
)
from engines.realtime.timeline import get_timeline_store
from engines.routing.registry import ResourceRoute, routing_registry


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RoutingControlPlaneService:
    """Service for managing routing registry with audit and stream event emission."""
    
    def __init__(self):
        self._registry = routing_registry()
        self._timeline_store = get_timeline_store()
    
    def upsert_route(self, route: ResourceRoute, context: RequestContext) -> ResourceRoute:
        """Upsert a route with audit and stream event emission.
        
        Lane 5: Detects backend type changes and records switch history.
        
        Args:
            route: ResourceRoute to upsert
            context: RequestContext for audit/stream
        
        Returns:
            The upserted route
        """
        # Get existing route to detect backend change
        existing = self._registry.get_route(
            route.resource_kind, 
            route.tenant_id, 
            route.env, 
            route.project_id
        )
        
        # If backend_type changed and no previous_backend_type set, record the switch time
        is_backend_change = existing and existing.backend_type != route.backend_type
        if is_backend_change and not route.last_switch_time:
            route.last_switch_time = _utc_now()
        
        # Upsert to registry
        created = self._registry.upsert_route(route)
        
        # Emit audit event
        emit_audit_event(
            context,
            action="routing:upsert",
            surface="routing",
            metadata={
                "resource_kind": route.resource_kind,
                "tenant_id": route.tenant_id,
                "env": route.env,
                "project_id": route.project_id,
                "backend_type": route.backend_type,
                "previous_backend_type": route.previous_backend_type,
                "switch_rationale": route.switch_rationale,
            },
            output_data={"route_id": route.id},
        )
        
        # Emit stream event (ROUTE_CHANGED or ROUTE_BACKEND_SWITCHED)
        event_type = "ROUTE_BACKEND_SWITCHED" if is_backend_change else "ROUTE_CHANGED"
        self._emit_route_event(
            context,
            event_type=event_type,
            route=created,
            action="upsert",
        )
        
        return created
    
    def get_route(
        self,
        resource_kind: str,
        tenant_id: str,
        env: str,
        project_id: Optional[str] = None,
    ) -> Optional[ResourceRoute]:
        """Get a route from registry (no stream event)."""
        return self._registry.get_route(resource_kind, tenant_id, env, project_id)
    
    def list_routes(
        self,
        resource_kind: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[ResourceRoute]:
        """List routes matching optional filters (no stream event)."""
        return self._registry.list_routes(resource_kind, tenant_id)
    
    def delete_route(
        self,
        resource_kind: str,
        tenant_id: str,
        env: str,
        project_id: Optional[str] = None,
        context: Optional[RequestContext] = None,
    ) -> None:
        """Delete a route with optional audit and stream event emission."""
        self._registry.delete_route(resource_kind, tenant_id, env, project_id)
        
        if context:
            emit_audit_event(
                context,
                action="routing:delete",
                surface="routing",
                metadata={
                    "resource_kind": resource_kind,
                    "tenant_id": tenant_id,
                    "env": env,
                    "project_id": project_id,
                },
            )
    
    def _emit_route_event(
        self,
        context: RequestContext,
        event_type: str,
        route: ResourceRoute,
        action: str,
    ) -> None:
        """Emit a stream event for route changes (Lane 5: includes switch history)."""
        try:
            actor_id = context.user_id or context.actor_id or "system"
            routing_keys = RoutingKeys(
                tenant_id=context.tenant_id,
                mode=context.mode,
                env=context.env,
                project_id=context.project_id,
                app_id=context.app_id,
                surface_id=context.surface_id,
                actor_id=actor_id,
                actor_type=ActorType.HUMAN if context.user_id else ActorType.SYSTEM,
            )
            
            # Lane 5: Include switch history in event data
            event_data = {
                "action": action,
                "resource_kind": route.resource_kind,
                "backend_type": route.backend_type,
                "route_id": route.id,
            }
            
            # Include switch history if available
            if route.previous_backend_type:
                event_data["previous_backend_type"] = route.previous_backend_type
            if route.switch_rationale:
                event_data["switch_rationale"] = route.switch_rationale
            if route.last_switch_time:
                event_data["last_switch_time"] = route.last_switch_time.isoformat()
            
            event = StreamEvent(
                type=event_type,
                ts=_utc_now(),
                event_id=str(uuid4()),
                routing=routing_keys,
                ids=EventIds(
                    request_id=context.request_id,
                    trace_id=context.trace_id or context.request_id,
                    run_id=context.run_id,
                    step_id=context.step_id,
                ),
                data=event_data,
                meta=EventMeta(
                    priority=EventPriority.TRUTH,
                    persist=PersistPolicy.ALWAYS,
                ),
            )
            
            # Emit to routing stream (routing/{tenant_id})
            stream_id = f"routing/{context.tenant_id}"
            self._timeline_store.append(stream_id, event, context)
        except Exception as exc:
            # Non-fatal: log but don't block route operation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to emit route event: {exc}")
