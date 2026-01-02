"""Filesystem-backed timeline store for realtime stream events (Lane 2 adapter).

Provides durable event storage using filesystem append-log pattern.
Location: var/event_stream/{tenant_id}/{mode_or_env}/{surface_id or "global"}/events.jsonl
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id
from engines.realtime.contracts import StreamEvent

logger = logging.getLogger(__name__)


class FileSystemTimelineStore:
    """Filesystem-backed timeline store using JSONL append-log pattern.
    
    Path structure:
      var/event_stream/{tenant_id}/{env}/{surface_id or "_"}/events.jsonl
    
    Guarantees:
      - Append-only (never overwrites existing events)
      - Survive restart (persisted to disk)
      - Monotonic by append order (file position = event order)
    """
    
    def __init__(self, base_dir: Optional[str | Path] = None) -> None:
        self._base_dir = Path(base_dir or Path.cwd() / "var" / "event_stream")
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _stream_dir(self, stream_id: str, context: RequestContext) -> Path:
        """Deterministic directory path for a stream.
        
        stream_id typically: thread_id, canvas_id, or resource-specific identifier
        We organize by tenant/env/surface for easier debugging.
        """
        surface = normalize_surface_id(context.surface_id) if context.surface_id else "_"
        env = (context.env or "dev").lower()
        tenant = context.tenant_id
        
        # stream_id as filename component (sanitized to avoid path issues)
        safe_stream_id = stream_id.replace("/", "_").replace("..", "_")
        
        return self._base_dir / tenant / env / surface / safe_stream_id
    
    def _events_file(self, stream_id: str, context: RequestContext) -> Path:
        """Full path to the JSONL events file."""
        return self._stream_dir(stream_id, context) / "events.jsonl"
    
    def append(self, stream_id: str, event: StreamEvent, context: RequestContext) -> None:
        """Append a StreamEvent to the timeline (append-only).
        
        Enforces backend-class guard: filesystem backend forbidden in sellable modes.
        """
        if context is None:
            raise RuntimeError("RequestContext is required for timeline append")
        
        # Backend-class guard (Lane 2): forbid filesystem in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=event_stream, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        # Validate scope match (same checks as in-memory)
        routing = event.routing
        if routing.tenant_id != context.tenant_id:
            raise RuntimeError("Timeline routing tenant mismatch")
        if routing.mode and routing.mode != context.mode:
            raise RuntimeError("Timeline routing mode mismatch")
        
        # Ensure directory exists
        file_path = self._events_file(stream_id, context)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append event as JSON line (append-only, no overwrite)
        try:
            with open(file_path, "a") as f:
                # Use mode='json' for Pydantic v2 serialization
                f.write(json.dumps(event.model_dump(mode="json")) + "\n")
        except Exception as exc:
            logger.error(f"Failed to append timeline event to {file_path}: {exc}")
            raise RuntimeError(f"Timeline append failed: {exc}") from exc
    
    def list_after(
        self, 
        stream_id: str, 
        after_event_id: Optional[str] = None,
        context: Optional[RequestContext] = None,
    ) -> List[StreamEvent]:
        """List events in order, optionally after a specific event_id."""
        # Note: for filesystem, we need context to know the path
        # If not provided, we cannot reliably determine the correct file path
        # For backward compat, we accept None but log a warning
        if context is None:
            logger.warning(
                "list_after called without RequestContext; "
                "assuming default env=dev, surface=_"
            )
            from engines.common.identity import RequestContext as RC
            context = RC(tenant_id="t_system", env="dev")
        
        events: List[StreamEvent] = []
        file_path = self._events_file(stream_id, context)
        
        if not file_path.exists():
            return events
        
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        event = StreamEvent(**data)
                        events.append(event)
                    except Exception as exc:
                        logger.warning(f"Skipping malformed timeline line in {file_path}: {exc}")
                        continue
        except Exception as exc:
            logger.error(f"Failed to read timeline from {file_path}: {exc}")
            return []
        
        # Filter to events after specified event_id
        if not after_event_id:
            return events
        
        for idx, ev in enumerate(events):
            if ev.event_id == after_event_id:
                return events[idx + 1 :]
        
        # Event not found; return all events (conservative)
        logger.warning(
            f"Requested event_id {after_event_id} not found in stream {stream_id}; "
            "returning all events"
        )
        return events
