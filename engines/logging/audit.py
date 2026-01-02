"""Audit helper for emitting DatasetEvents for sensitive actions."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_dataset_event

logger = logging.getLogger(__name__)
_audit_logger = log_dataset_event


def set_audit_logger(logger) -> None:
    global _audit_logger
    _audit_logger = logger


def emit_audit_event(
    ctx: RequestContext,
    action: str,
    surface: str = "audit",
    metadata: Optional[Dict[str, Any]] = None,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
) -> None:
    actor_type = "human" if ctx.user_id else "system"
    base_metadata = {
        "action": action,
        "actor_type": actor_type,
        "request_id": ctx.request_id,
        "trace_id": ctx.request_id,
    }
    if metadata:
        base_metadata.update(metadata)

    event = DatasetEvent(
        tenantId=ctx.tenant_id,
        env=ctx.env,
        surface=surface,
        agentId=ctx.user_id or "system",
        input=input_data or {},
        output=output_data or {},
        metadata=base_metadata,
        analytics_event_type="audit",
        analytics_platform="internal",
        traceId=ctx.request_id,
        requestId=ctx.request_id,
        actorType=actor_type,
    )
    result = _audit_logger(event)
    if not result or result.get("status") != "accepted":
        detail = result.get("error", "audit persistence failed")
        if os.environ.get("AUDIT_STRICT") == "1":
            raise RuntimeError(detail)
        logger.warning("audit persistence failed: %s", detail)
