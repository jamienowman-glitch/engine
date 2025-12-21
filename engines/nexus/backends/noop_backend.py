"""No-op backend for offline/testing."""
from __future__ import annotations

from typing import Any, Dict, List


class NoopNexusBackend:
    def __init__(self) -> None:
        self.events: List[Any] = []

    def write_event(self, event) -> Dict[str, str]:
        self.events.append(event)
        return {"status": "noop"}
