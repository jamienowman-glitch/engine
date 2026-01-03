"""Event spine service with reject-on-missing-route behavior (TL-01).

Enforces routed-only append and cursor-based replay.
Missing route raises MissingEventSpineRoute (HTTP 503, error_code: event_spine.missing_route).
No in-memory or filesystem fallbacks.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.event_spine.cloud_event_spine_store import SpineEvent
from engines.event_spine.validation_service import EventSpineValidator

logger = logging.getLogger(__name__)


class MissingEventSpineRoute(Exception):
    """Raised when event_spine route is missing (HTTP 503)."""
    
    def __init__(self, context: RequestContext):
        self.error_code = "event_spine.missing_route"
        self.status_code = 503
        self.message = (
            f"Event spine route not configured for tenant={context.tenant_id}, "
            f"env={context.env}. Configure via /routing/routes with "
            f"resource_kind=event_spine and backend_type=firestore|dynamodb|cosmos."
        )
        super().__init__(self.message)


class EventSpineServiceRejectOnMissing:
    """Event spine service with reject-on-missing-route behavior (TL-01 compliance).
    
    - Append-only append() for events
    - Cursor-based replay() for timeline reconstruction
    - Rejects (raises MissingEventSpineRoute, HTTP 503) if route missing
    - No fallbacks; no in-memory; no filesystem
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._validator = EventSpineValidator()
        self._adapter = self._resolve_adapter_or_reject()
    
    def _resolve_adapter_or_reject(self):
        """Resolve event_spine backend via routing registry.
        
        Raises MissingEventSpineRoute (HTTP 503) if route missing or misconfigured.
        """
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="event_spine",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                raise MissingEventSpineRoute(self._context)
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                from engines.event_spine.cloud_event_spine_store import FirestoreEventSpineStore
                project = config.get("project")
                return FirestoreEventSpineStore(project=project)
            elif backend_type == "dynamodb":
                from engines.event_spine.cloud_event_spine_store import DynamoDBEventSpineStore
                table_name = config.get("table_name", "event_spine")
                region = config.get("region", "us-west-2")
                return DynamoDBEventSpineStore(table_name=table_name, region=region)
            elif backend_type == "cosmos":
                from engines.event_spine.cloud_event_spine_store import CosmosEventSpineStore
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "event_spine")
                return CosmosEventSpineStore(endpoint=endpoint, key=key, database=database)
            else:
                raise MissingEventSpineRoute(self._context)
        except MissingEventSpineRoute:
            raise
        except MissingRoutingConfig:
            raise MissingEventSpineRoute(self._context)
        except Exception as e:
            logger.error(f"Failed to resolve event_spine backend: {e}")
            raise MissingEventSpineRoute(self._context) from e
    
    def append(
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
        """Append event to spine (append-only).
        
        Raises MissingEventSpineRoute if route missing.
        
        Returns: event_id (UUID).
        """
        # Validate event shape
        validation = self._validator.validate(
            tenant_id=self._context.tenant_id,
            mode=self._context.mode,
            event_type=event_type,
            source=source,
            run_id=run_id,
            user_id=user_id,
            surface_id=surface_id,
            project_id=project_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
        )
        
        if not validation.is_valid:
            error_msg = f"Event validation failed: {'; '.join(validation.errors)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
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
        
        try:
            self._adapter.append(event, self._context)
            logger.debug(f"Appended event {event.event_id} to event_spine")
            return event.event_id
        except Exception as e:
            logger.error(f"Failed to append event to spine: {e}")
            raise RuntimeError(f"Event append failed: {e}") from e
    
    def replay(
        self,
        run_id: str,
        after_event_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SpineEvent]:
        """Cursor-based replay of events from spine (read-only).
        
        Used for timeline reconstruction across restarts.
        
        Args:
            run_id: filter by run
            after_event_id: cursor - only return events after this event_id (by timestamp)
            event_type: optional event type filter
            limit: max events to return
        
        Returns: list of SpineEvent ordered by timestamp.
        Raises MissingEventSpineRoute if route missing.
        """
        try:
            events = self._adapter.list_events(
                tenant_id=self._context.tenant_id,
                run_id=run_id,
                event_type=event_type,
                after_event_id=after_event_id,
                limit=limit,
            )
            logger.debug(f"Replayed {len(events)} events for run {run_id} (cursor={after_event_id})")
            return events
        except Exception as e:
            logger.error(f"Failed to replay events: {e}")
            raise RuntimeError(f"Event replay failed: {e}") from e
    
    def list_events(
        self,
        run_id: str,
        event_type: Optional[str] = None,
        after_event_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SpineEvent]:
        """Alias for replay() for consistency with read operations."""
        return self.replay(run_id, after_event_id, event_type, limit)
