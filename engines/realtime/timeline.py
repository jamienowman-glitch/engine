"""Durable timeline store for realtime stream events."""
from __future__ import annotations

import logging
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
    
    Routes event_stream resource_kind to appropriate backend via routing registry.
    Supports:
    - filesystem (lab-only, requires routing entry + lab mode)
    - firestore (cloud backend, requires GCP credentials)
    
    Fails fast with explicit error if:
    - No route configured for event_stream
    - Backend type is unsupported
    - Filesystem backend in sellable modes (saas/enterprise/t_system)
    
    NOTE: env var STREAM_TIMELINE_BACKEND no longer used (Lane 3 removes env gates).
    """
    from engines.routing.registry import routing_registry, MissingRoutingConfig
    from engines.realtime.filesystem_timeline import FileSystemTimelineStore
    
    registry = routing_registry()
    # Try to resolve route for event_stream kind (tenant=t_system, env as baseline)
    route = registry.get_route(
        resource_kind="event_stream",
        tenant_id="t_system",
        env="dev",  # Baseline for startup resolution
    )
    
    if not route:
        raise RuntimeError(
            "No route configured for event_stream. "
            "Create a route via /routing/routes with backend_type='filesystem' (lab only) or 'firestore' (cloud)."
        )
    
    backend_type = (route.backend_type or "").lower()
    
    if backend_type == "filesystem":
        return FileSystemTimelineStore()
    elif backend_type == "firestore":
        return FirestoreTimelineStore()
    else:
        raise RuntimeError(
            f"Unsupported event_stream backend_type='{backend_type}'. "
            f"Use 'filesystem' (lab-only) or 'firestore' (cloud)."
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
