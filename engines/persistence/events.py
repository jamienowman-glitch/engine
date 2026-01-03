"""Helpers for emitting persistence events to the event spine."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.event_spine.validation_service import EventSpineServiceWithValidation

logger = logging.getLogger(__name__)


def emit_persistence_event(
    context: RequestContext,
    resource: str,
    action: str,
    record_id: str,
    version: int,
    event_type: str = "audit",
    extra_payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit a structured persistence event via Agent A's spine API."""
    run_id = context.run_id or context.request_id
    payload: Dict[str, Any] = {
        "resource": resource,
        "action": action,
        "record_id": record_id,
        "version": version,
    }
    if extra_payload:
        payload.update(extra_payload)
    try:
        spine = EventSpineServiceWithValidation(context)
        spine.emit(
            event_type=event_type,
            source="agent",
            run_id=str(run_id),
            payload=payload,
            surface_id=context.surface_id,
            project_id=context.project_id,
            step_id=context.step_id,
            parent_event_id=None,
            trace_id=context.trace_id,
            span_id=None,
        )
    except Exception as exc:
        logger.warning("Failed to emit %s/%s event: %s", resource, action, exc)
