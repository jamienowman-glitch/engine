"""Vector Explorer ingest service with Gate1 PII boundary enforcement."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from engines.common.identity import RequestContext
from engines.logging.event_sink import DatasetEventSink, build_dataset_event
from engines.security.pii import PIIRehydrationHook, redact_text

logger = logging.getLogger(__name__)


class VectorIngestService:
    """Sanitizes documents before embedding with Nexus tooling."""

    def __init__(
        self,
        event_sink: DatasetEventSink,
        rehydration_hook: Optional[PIIRehydrationHook] = None,
    ) -> None:
        self._event_sink = event_sink
        self._rehydration_hook = rehydration_hook

    def ingest(self, ctx: RequestContext, documents: List[str]) -> dict[str, List[float]]:
        """Redact all documents, emit an event, and return placeholder embeddings."""
        sanitized_documents: List[str] = []
        aggregated_flags: Dict[str, bool] = {}
        for document in documents:
            sanitized, pii_flags, _ = redact_text(document)
            sanitized_documents.append(sanitized)
            for label, detected in pii_flags.items():
                aggregated_flags[label] = aggregated_flags.get(label, False) or detected

        train_ok = not any(aggregated_flags.values())
        combined_text = "\n".join(sanitized_documents)
        event = build_dataset_event(
            ctx=ctx,
            sanitized_text=combined_text,
            pii_flags=aggregated_flags,
            train_ok=train_ok,
            event_type="vector_ingest",
            agent_id="vector_explorer_ingest",
            metadata={"document_count": len(documents)},
        )
        self._event_sink.record(event)

        logger.info(
            "Vector ingest sanitized=%s pii_flags=%s tenant=%s",
            sanitized_documents,
            aggregated_flags,
            ctx.tenant_id,
        )
        embeddings = [self._simulate_embedding(text) for text in sanitized_documents]
        return {"documents": sanitized_documents, "embeddings": embeddings}

    def rehydrate_document(self, sanitized: str, ctx: RequestContext) -> str:
        """Rehydrate a sanitized document when a hook is provided."""
        if not self._rehydration_hook:
            raise NotImplementedError("No rehydration hook configured")
        return self._rehydration_hook.rehydrate(sanitized, ctx)

    def _simulate_embedding(self, sanitized: str) -> List[float]:
        """Deterministic placeholder embedding for the sanitized document."""
        length = len(sanitized)
        magnitude = sum(ord(char) for char in sanitized) if sanitized else 0
        return [float(length), float(magnitude / 100)]
