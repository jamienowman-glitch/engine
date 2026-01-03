"""Event spine validation and warning-first diagnostics (Agent A - A-2).

Enforces event shape (tenant/mode/run/step/parent required fields).
Implements warning-first behavior: missing route logs warning and continues,
does not emit but operations proceed. No stdout fallback, no startup failure.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from enum import Enum

from engines.common.identity import RequestContext
from engines.routing.registry import MissingRoutingConfig, routing_registry
from engines.event_spine.cloud_event_spine_store import SpineEvent

logger = logging.getLogger(__name__)


class EventValidationError(Exception):
    """Raised when event shape validation fails."""
    pass


class EventValidationResult:
    """Result of event validation (success or error)."""
    
    def __init__(self, is_valid: bool, errors: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []


class EventSpineValidator:
    """Validates event shape and enforces required fields.
    
    Required fields:
    - tenant_id: ownership (from context)
    - mode: environment (from context)
    - event_type: analytics|audit|safety|rl|rlha|tuning|budget|strategy_lock|...
    - source: ui|agent|connector|tool
    - run_id: provenance identifier
    
    Optional but recommended:
    - user_id, surface_id, project_id: scoping
    - step_id, parent_event_id: causality
    - trace_id, span_id: distributed tracing
    """
    
    VALID_EVENT_TYPES = {
        "analytics", "audit", "safety", "rl", "rlha", "tuning", 
        "budget", "strategy_lock", "gatechainerror"
    }
    VALID_SOURCES = {"ui", "agent", "connector", "tool"}
    
    def validate(
        self,
        tenant_id: str,
        mode: str,
        event_type: str,
        source: str,
        run_id: str,
        user_id: Optional[str] = None,
        surface_id: Optional[str] = None,
        project_id: Optional[str] = None,
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
    ) -> EventValidationResult:
        """Validate event shape.
        
        Returns EventValidationResult with is_valid=True if all required fields present
        and well-formed.
        """
        errors = []
        
        # Required field validation
        if not tenant_id or not isinstance(tenant_id, str):
            errors.append("tenant_id is required and must be a string")
        if not mode or not isinstance(mode, str):
            errors.append("mode is required and must be a string")
        if not event_type or event_type not in self.VALID_EVENT_TYPES:
            errors.append(f"event_type must be one of {self.VALID_EVENT_TYPES}, got '{event_type}'")
        if not source or source not in self.VALID_SOURCES:
            errors.append(f"source must be one of {self.VALID_SOURCES}, got '{source}'")
        if not run_id or not isinstance(run_id, str):
            errors.append("run_id is required and must be a string")
        
        # Optional field validation (type checks only)
        if user_id and not isinstance(user_id, str):
            errors.append("user_id must be a string")
        if surface_id and not isinstance(surface_id, str):
            errors.append("surface_id must be a string")
        if project_id and not isinstance(project_id, str):
            errors.append("project_id must be a string")
        if step_id and not isinstance(step_id, str):
            errors.append("step_id must be a string")
        if parent_event_id and not isinstance(parent_event_id, str):
            errors.append("parent_event_id must be a string")
        
        return EventValidationResult(is_valid=len(errors) == 0, errors=errors)


class EventSpineServiceWithValidation:
    """Event spine service with validation and warning-first diagnostics (A-2).
    
    Validates all events. If route missing:
    - Log warning at startup
    - Log warning on emit attempt
    - Do NOT emit (operation proceeds)
    - Do NOT crash startup
    - Do NOT fall back to stdout or in-memory
    
    This service is a wrapper around EventSpineService that adds:
    1. Event shape validation
    2. Warning-first route checking
    3. Graceful degradation (warn and skip emit, don't fail operations)
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._validator = EventSpineValidator()
        self._adapter = None
        self._route_missing = False
        self._route_missing_logged = False
        
        # Try to resolve route; if missing, log warning and set flag
        self._check_route()
    
    def _check_route(self) -> None:
        """Check if event_spine route exists. Log warning if missing."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="event_spine",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            
            if not route:
                self._route_missing = True
                logger.warning(
                    f"event_spine route not configured for tenant={self._context.tenant_id}, "
                    f"env={self._context.env}. Events will not be persisted. "
                    f"Configure via /routing/routes with resource_kind=event_spine."
                )
            else:
                # Route exists, initialize adapter
                self._initialize_adapter(route)
        except Exception as e:
            self._route_missing = True
            logger.warning(f"Failed to check event_spine route: {e}. Events will not be persisted.")
    
    def _initialize_adapter(self, route):
        """Initialize the backend adapter given a route."""
        try:
            from engines.event_spine.cloud_event_spine_store import (
                FirestoreEventSpineStore,
                DynamoDBEventSpineStore,
                CosmosEventSpineStore,
            )
            
            backend_type = (route.backend_type or "").lower()
            config = route.config or {}
            
            if backend_type == "firestore":
                self._adapter = FirestoreEventSpineStore(project=config.get("project"))
            elif backend_type == "dynamodb":
                self._adapter = DynamoDBEventSpineStore(
                    table_name=config.get("table_name", "event_spine"),
                    region=config.get("region", "us-west-2"),
                )
            elif backend_type == "cosmos":
                self._adapter = CosmosEventSpineStore(
                    endpoint=config.get("endpoint"),
                    key=config.get("key"),
                    database=config.get("database", "event_spine"),
                )
            else:
                self._route_missing = True
                logger.warning(
                    f"Unsupported event_spine backend_type='{backend_type}'. "
                    f"Use 'firestore', 'dynamodb', or 'cosmos'."
                )
        except Exception as e:
            self._route_missing = True
            logger.warning(f"Failed to initialize event_spine adapter: {e}. Events will not be persisted.")
    
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
    ) -> Optional[str]:
        """Emit event to spine with validation and warning-first behavior.
        
        If route missing:
        - Log warning (once per process)
        - Skip emit
        - Return None
        - Continue operation
        
        If validation fails:
        - Log error
        - Skip emit
        - Return None
        
        Returns: event_id if emit succeeded, None if skipped.
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
            logger.error(
                f"Event validation failed: {'; '.join(validation.errors)}. "
                f"Event (type={event_type}, run={run_id}) not emitted."
            )
            return None
        
        # Check route
        if self._route_missing:
            if not self._route_missing_logged:
                logger.warning(
                    f"event_spine route not configured. Event (type={event_type}, run={run_id}) "
                    f"not emitted. This is the only warning message for this session."
                )
                self._route_missing_logged = True
            return None
        
        # Emit to backend
        try:
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
            
            self._adapter.append(event, self._context)
            logger.debug(f"Emitted event {event.event_id} to event_spine")
            return event.event_id
        except Exception as e:
            logger.error(f"Failed to emit event to spine: {e}")
            return None
    
    def list_events(
        self,
        run_id: str,
        event_type: Optional[str] = None,
    ) -> List[SpineEvent]:
        """Query spine events (read-only).
        
        If route missing, returns empty list (graceful degradation).
        """
        if self._route_missing or not self._adapter:
            return []
        
        try:
            return self._adapter.list_events(
                tenant_id=self._context.tenant_id,
                run_id=run_id,
                event_type=event_type,
            )
        except Exception as e:
            logger.error(f"Failed to query event spine: {e}")
            return []
