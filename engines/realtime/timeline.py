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
        started = after_event_id is None
        for snap in snaps:
            data = snap.to_dict() or {}
            try:
                ev = StreamEvent(**data)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping invalid timeline event: %s", exc)
                continue
            if started:
                events.append(ev)
            elif ev.event_id == after_event_id:
                started = True
        if after_event_id and started and events:
            events = events[1:]
        return events


class FileTimelineStore:
    def __init__(self, path: str = "timeline_store.json"):
        self.path = path
        import json, os
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump({}, f)

    def _load(self) -> Dict[str, List[dict]]:
        import json
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data: Dict[str, List[dict]]) -> None:
        import json
        with open(self.path, "w") as f:
            json.dump(data, f, default=str)

    def append(self, stream_id: str, event: StreamEvent, context: RequestContext) -> None:
        if context is None:
            raise RuntimeError("RequestContext is required for timeline append")
        data = self._load()
        bucket = data.get(stream_id, [])
        # event.dict() might contain non-serializable datetimes, use json() then loads?
        # StreamEvent is pydantic.
        import json
        bucket.append(json.loads(event.json()))
        data[stream_id] = bucket
        self._save(data)

    def list_after(self, stream_id: str, after_event_id: Optional[str] = None) -> List[StreamEvent]:
        data = self._load()
        raw_events = data.get(stream_id, [])
        events = []
        for r in raw_events:
            try:
                events.append(StreamEvent(**r))
            except:
                pass
        
        if not after_event_id:
            return events
            
        for idx, ev in enumerate(events):
            if ev.event_id == after_event_id:
                return events[idx + 1 :]
        return []

def _default_timeline_store() -> TimelineStore:
    backend = (os.getenv("STREAM_TIMELINE_BACKEND") or "").lower()
    if backend == "filesystem":
        return FileTimelineStore()
    if backend in {"", "memory"}:
        raise RuntimeError("STREAM_TIMELINE_BACKEND must be set to 'firestore'")
    if backend == "firestore":
        return FirestoreTimelineStore()
    raise RuntimeError(f"Unsupported STREAM_TIMELINE_BACKEND '{backend}'")


_timeline_store: Optional[TimelineStore] = None


def get_timeline_store() -> TimelineStore:
    global _timeline_store
    if _timeline_store is None:
        _timeline_store = _default_timeline_store()
    return _timeline_store


def set_timeline_store(store: TimelineStore) -> None:
    global _timeline_store
    _timeline_store = store
