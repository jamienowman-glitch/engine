"""Vector Explorer query service that enforces PII redaction before outbound calls."""

from __future__ import annotations

import logging
from typing import Optional

from engines.common.identity import RequestContext
from engines.logging.event_sink import DatasetEventSink, build_dataset_event
from engines.security.pii import PIIRehydrationHook, redact_text

logger = logging.getLogger(__name__)


class VectorExplorerService:
    """Sanitizes queries before talking to Nexus vector tooling."""

    def __init__(
        self,
        event_sink: DatasetEventSink,
        rehydration_hook: Optional[PIIRehydrationHook] = None,
    ) -> None:
        self._event_sink = event_sink
        self._rehydration_hook = rehydration_hook

    def query(self, ctx: RequestContext, query_text: str) -> dict[str, object]:
        """Redact the query, emit an event, and return sanitized results."""
        sanitized, pii_flags, train_ok = redact_text(query_text)
        logger.info(
            "Vector query sanitized=%s pii_flags=%s tenant=%s",
            sanitized,
            pii_flags,
            ctx.tenant_id,
        )
        event = build_dataset_event(
            ctx=ctx,
            sanitized_text=sanitized,
            pii_flags=pii_flags,
            train_ok=train_ok,
            event_type="vector_query",
            agent_id="vector_explorer_query",
            metadata={"service": "vector_explorer"},
        )
        self._event_sink.record(event)
        return {
            "query": sanitized,
            "matches": [{"id": "vector-match-a", "score": 0.92}],
        }

    def rehydrate_query(self, sanitized: str, ctx: RequestContext) -> str:
        """Rehydrate sanitized queries if a hook is configured."""
        if not self._rehydration_hook:
            raise NotImplementedError("No rehydration hook configured")
        return self._rehydration_hook.rehydrate(sanitized, ctx)
