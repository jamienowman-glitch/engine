"""Helpers for recording dataset events while honoring Gate1 envelopes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from engines.common.identity import RequestContext
from engines.dataset.events.contract import DatasetEvent, build_envelope_from_context


class DatasetEventSink(Protocol):
    """Protocol for emitting or recording dataset events."""

    def record(self, event: DatasetEvent) -> None:
        """Record or forward the dataset event."""


class InMemoryEventSink(DatasetEventSink):
    """In-memory sink useful for unit tests."""

    def __init__(self) -> None:
        self.events: List[DatasetEvent] = []

    def record(self, event: DatasetEvent) -> None:
        self.events.append(event)


def build_dataset_event(
    ctx: RequestContext,
    sanitized_text: str,
    pii_flags: Dict[str, bool],
    train_ok: bool,
    event_type: str,
    agent_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> DatasetEvent:
    """
    Build a DatasetEvent using Gate1 envelope enforcement and redaction metadata.
    """
    envelope = build_envelope_from_context(ctx)
    additional_data = dict(metadata) if metadata else {}
    return DatasetEvent(
        envelope=envelope,
        event_type=event_type,
        agent_id=agent_id,
        input_text=sanitized_text,
        pii_flags=pii_flags,
        train_ok=train_ok,
        additional_data=additional_data,
    )
