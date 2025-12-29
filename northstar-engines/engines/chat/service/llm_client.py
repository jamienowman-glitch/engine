"""LLM client that enforces Gate1 PII redaction before outbound calls."""

from __future__ import annotations

import logging
from typing import Optional

from engines.common.identity import RequestContext
from engines.logging.event_sink import DatasetEventSink, build_dataset_event
from engines.security.pii import PIIRehydrationHook, redact_text

logger = logging.getLogger(__name__)


class LLMClient:
    """Wraps outbound LLM calls with PII redaction + event emission."""

    def __init__(
        self,
        event_sink: DatasetEventSink,
        rehydration_hook: Optional[PIIRehydrationHook] = None,
    ) -> None:
        self._event_sink = event_sink
        self._rehydration_hook = rehydration_hook

    def call(self, prompt: str, ctx: RequestContext) -> str:
        """Redact the prompt, emit an event, and return the sanitized response."""
        sanitized, pii_flags, train_ok = redact_text(prompt)
        logger.info(
            "LLM call sanitized prompt=%s pii_flags=%s tenant=%s",
            sanitized,
            pii_flags,
            ctx.tenant_id,
        )
        event = build_dataset_event(
            ctx=ctx,
            sanitized_text=sanitized,
            pii_flags=pii_flags,
            train_ok=train_ok,
            event_type="llm_prompt",
            agent_id="llm_client",
            metadata={"service": "llm_client"},
        )
        self._event_sink.record(event)
        return self._simulate_remote_call(sanitized)

    def rehydrate_payload(self, sanitized: str, ctx: RequestContext) -> str:
        """Rehydrate sanitized prompts for authorized tooling via hook."""
        if not self._rehydration_hook:
            raise NotImplementedError("No rehydration hook configured")
        return self._rehydration_hook.rehydrate(sanitized, ctx)

    def _simulate_remote_call(self, sanitized_prompt: str) -> str:
        """Simulated external call that only sees sanitized text."""
        return f"llm-response:{sanitized_prompt}"
