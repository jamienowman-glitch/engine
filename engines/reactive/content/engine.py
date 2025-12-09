"""Reactive content watcher scaffold."""
from __future__ import annotations

from typing import List

from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_event


def watch(event: DatasetEvent) -> List[DatasetEvent]:
    created: List[DatasetEvent] = []
    evt_type = event.analytics_event_type or (event.metadata.get("type") if event.metadata else None)
    if evt_type == "content.published.youtube_video":
        followups = [
            "content.reactive.blog_candidate",
            "content.reactive.email_candidate",
        ]
        for kind in followups:
            new_evt = DatasetEvent(
                tenantId=event.tenantId,
                env=event.env,
                surface="content",
                agentId="reactive-content",
                input={"source_event": event.dict()},
                output={"suggestion_kind": kind, "title": event.metadata.get("title") if event.metadata else None},
                analytics_event_type=kind,
                metadata={"kind": kind},
            )
            log_event(new_evt)
            created.append(new_evt)
    return created
