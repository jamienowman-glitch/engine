"""In-Memory Nexus Backend for Phase 7 Research Runs (non-persistent)."""
from __future__ import annotations

import typing
from datetime import datetime, timezone
from typing import Any, List, Optional

from engines.dataset.events.schemas import DatasetEvent

# Module-level store to simulate persistence across multiple get_backend() calls
_GLOBAL_EVENTS: List[DatasetEvent] = []


class InMemoryNexusBackend:
    def __init__(self, client: Any = None):
        pass

    def write_event(self, event: DatasetEvent) -> None:
        """Store event in memory."""
        # Ensure timestamp is set if missing (though usually schema handles it)
        # We append to global list
        _GLOBAL_EVENTS.append(event)

    def query_events(
        self, 
        tenant_id: str, 
        env: str, 
        limit: int = 100
    ) -> List[DatasetEvent]:
        """
        Query events matching tenant and env.
        Returns most recent first.
        """
        # Filter
        matches = [
            e for e in _GLOBAL_EVENTS 
            if e.tenantId == tenant_id and e.env == env
        ]
        # Sort desc by timestamp (assuming capturing logic or order of insertion)
        # DatasetEvent doesn't explicitly guarantee a 'timestamp' field in schema top-level 
        # (it's in metadata usually, or not present in schema def we saw earlier?).
        # Let's check schema. Inspecting previous `event_log.py` creates `DatasetEvent`.
        # Schema likely has it or we rely on insertion order (reverse).
        
        matches.reverse()
        return matches[:limit]
