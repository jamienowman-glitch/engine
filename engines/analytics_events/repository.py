from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.analytics_events.models import AnalyticsEventRecord


class AnalyticsEventRepository(Protocol):
    def record(self, record: AnalyticsEventRecord) -> AnalyticsEventRecord: ...
    def list(self, tenant_id: str, env: str, limit: int = 200, offset: int = 0) -> List[AnalyticsEventRecord]: ...


class InMemoryAnalyticsEventRepository:
    def __init__(self) -> None:
        self._items: List[AnalyticsEventRecord] = []

    def record(self, record: AnalyticsEventRecord) -> AnalyticsEventRecord:
        self._items.append(record)
        return record

    def list(self, tenant_id: str, env: str, limit: int = 200, offset: int = 0) -> List[AnalyticsEventRecord]:
        items = [r for r in self._items if r.tenant_id == tenant_id and r.env == env]
        return items[offset : offset + limit]


class FirestoreAnalyticsEventRepository(InMemoryAnalyticsEventRepository):
    """Firestore implementation."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore analytics events")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "analytics_events"

    def _col(self):
        return self._client.collection(self._collection)

    def record(self, record: AnalyticsEventRecord) -> AnalyticsEventRecord:
        self._col().document(record.id).set(record.model_dump())
        return record

    def list(self, tenant_id: str, env: str, limit: int = 200, offset: int = 0) -> List[AnalyticsEventRecord]:
        query = self._col().where("tenant_id", "==", tenant_id).where("env", "==", env).limit(limit + offset)
        results = [AnalyticsEventRecord(**d.to_dict()) for d in query.stream()]
        return results[offset : offset + limit]
