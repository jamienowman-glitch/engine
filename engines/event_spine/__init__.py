"""Event spine module (Agent A — Spine & Memory Track).

Provides:
- event_spine: append-only routed spine for analytics, audit, safety, RL, RLHA, tuning, budget, strategy
  - EventSpineServiceRejectOnMissing: TL-01 compliance (reject on missing route, HTTP 503)
  - Cursor-based replay for timeline reconstruction across restarts
- memory_store: persistent session memory with configurable TTL
- blackboard_store: persistent shared coordination state with versioning
"""

from engines.event_spine.service import EventSpineService
from engines.event_spine.service_reject import EventSpineServiceRejectOnMissing, MissingEventSpineRoute
from engines.event_spine.cloud_event_spine_store import SpineEvent

__all__ = [
    "EventSpineService",
    "EventSpineServiceRejectOnMissing",
    "MissingEventSpineRoute",
    "SpineEvent",
]
