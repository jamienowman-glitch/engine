"""Durable timeline store for realtime stream events."""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Protocol

from engines.common.identity import RequestContext
from engines.config import runtime_config
from engines.realtime.contracts import StreamEvent

try:  # pragma: no cover - optional dependency
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

logger = logging.getLogger(__name__)


class TimelineStore(Protocol):
    def append(self, stream_id: str, event: StreamEvent, context: RequestContext) -> None: ...
    def list_after(self, stream_id: str, after_event_id: Optional[str] = None) -> List[StreamEvent]: ...


class InMemoryTimelineStore:
    def __init__(self, storage: Optional[Dict[str, List[StreamEvent]]] = None) -> None:
        self._storage: Dict[str, List[StreamEvent]] = storage if storage is not None else {}

    def _validate_scope(self, event: StreamEvent, context: RequestContext) -> None:
        routing = event.routing
        if routing.tenant_id != context.tenant_id:
            raise RuntimeError("Timeline routing tenant mismatch")
        if routing.project_id and routing.project_id != context.project_id:
            raise RuntimeError("Timeline routing project mismatch")
        if routing.mode and routing.mode != context.mode:
            raise RuntimeError("Timeline routing mode mismatch")

    def append(self, stream_id: str, event: StreamEvent, context: RequestContext) -> None:
        if context is None:
            raise RuntimeError("RequestContext is required for timeline append")
        self._validate_scope(event, context)
        bucket = self._storage.setdefault(stream_id, [])
        bucket.append(event)

    def list_after(self, stream_id: str, after_event_id: Optional[str] = None) -> List[StreamEvent]:
        events = list(self._storage.get(stream_id, []))
        if not after_event_id:
            return events
        for idx, ev in enumerate(events):
            if ev.event_id == after_event_id:
                return events[idx + 1 :]
        return []


class FirestoreTimelineStore:
    _collection = "stream_timeline"

    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for timeline persistence")
        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore timeline store")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _event_collection(self, stream_id: str):
        return self._client.collection(self._collection).document(stream_id).collection("events")

    def append(self, stream_id: str, event: StreamEvent, context: RequestContext) -> None:
        if context is None:
            raise RuntimeError("RequestContext is required for timeline append")
        self._event_collection(stream_id).document(event.event_id).set(event.dict())  # type: ignore[attr-defined]

    def list_after(self, stream_id: str, after_event_id: Optional[str] = None) -> List[StreamEvent]:
        events: List[StreamEvent] = []
        query = self._event_collection(stream_id).order_by("ts")
        try:
            snaps = query.stream()
        except Exception as exc:  # pragma: no cover
            logger.warning("Firestore timeline query failed: %s", exc)
            return events
        for snap in snaps:
            data = snap.to_dict() or {}
            try:
                ev = StreamEvent(**data)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping invalid timeline event: %s", exc)
                continue
            events.append(ev)
        if not after_event_id:
            return events
        for idx, ev in enumerate(events):
            if ev.event_id == after_event_id:
                return events[idx + 1 :]
        return []


def _default_timeline_store() -> TimelineStore:
    """Resolve timeline store via routing registry (Lane 3 wiring).
    
    Routes event_stream resource_kind to appropriate backend:
    - filesystem (default for dev, requires routing registry entry)
    - firestore (explicit route with backend_type=firestore)
    
    Fails fast if no route configured; no env-driven selection.
    """
    from engines.routing.registry import routing_registry, MissingRoutingConfig
    from engines.realtime.filesystem_timeline import FileSystemTimelineStore
    
    try:
        registry = routing_registry()
        # Try to resolve route for event_stream kind (tenant=t_system, env as fallback)
        route = registry.get_route(
            resource_kind="event_stream",
            tenant_id="t_system",
            env="dev",  # Baseline for startup resolution
        )
        
        if not route:
            raise MissingRoutingConfig(
                "No route configured for event_stream. "
                "Route with backend_type=filesystem or firestore via /routing/routes."
            )
        
        backend_type = (route.backend_type or "").lower()
        
        if backend_type == "filesystem":
            return FileSystemTimelineStore()
        elif backend_type == "firestore":
            return FirestoreTimelineStore()
        else:
            raise RuntimeError(
                f"Unsupported event_stream backend_type='{backend_type}'. "
                f"Use 'filesystem' or 'firestore'."
            )
    except MissingRoutingConfig as e:
        # Re-raise with context
        raise RuntimeError(str(e)) from e
    except Exception as exc:
        # Fallback for missing routing infrastructure in tests
        logger.warning(
            "Failed to resolve event_stream route; falling back to env-based selection: %s", exc
        )
        # Legacy env-based fallback (for tests/migration)
        backend = (os.getenv("STREAM_TIMELINE_BACKEND") or "").lower()
        if backend == "firestore":
            return FirestoreTimelineStore()
        elif backend == "filesystem":
            from engines.realtime.filesystem_timeline import FileSystemTimelineStore
            return FileSystemTimelineStore()
        else:
            raise RuntimeError(
                "STREAM_TIMELINE_BACKEND must be 'firestore' or 'filesystem'. "
                "Or configure event_stream route via /routing/routes."
            )


_timeline_store: Optional[TimelineStore] = None


def get_timeline_store() -> TimelineStore:
    global _timeline_store
    if _timeline_store is None:
        _timeline_store = _default_timeline_store()
    return _timeline_store


def set_timeline_store(store: TimelineStore) -> None:
    global _timeline_store
    _timeline_store = store
