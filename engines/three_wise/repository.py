from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.three_wise.models import ThreeWiseRecord


class ThreeWiseRepository(Protocol):
    def create(self, record: ThreeWiseRecord) -> ThreeWiseRecord: ...
    def get(self, tenant_id: str, env: str, record_id: str) -> Optional[ThreeWiseRecord]: ...
    def list(self, tenant_id: str, env: str) -> List[ThreeWiseRecord]: ...
    def update(self, record: ThreeWiseRecord) -> ThreeWiseRecord: ...


class InMemoryThreeWiseRepository:
    def __init__(self) -> None:
        self._items: Dict[tuple[str, str, str], ThreeWiseRecord] = {}

    def create(self, record: ThreeWiseRecord) -> ThreeWiseRecord:
        self._items[(record.tenant_id, record.env, record.id)] = record
        return record

    def get(self, tenant_id: str, env: str, record_id: str) -> Optional[ThreeWiseRecord]:
        return self._items.get((tenant_id, env, record_id))

    def list(self, tenant_id: str, env: str) -> List[ThreeWiseRecord]:
        return [r for (t, e, _), r in self._items.items() if t == tenant_id and e == env]

    def update(self, record: ThreeWiseRecord) -> ThreeWiseRecord:
        self._items[(record.tenant_id, record.env, record.id)] = record
        return record


class FirestoreThreeWiseRepository(InMemoryThreeWiseRepository):
    """Firestore implementation."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore three-wise repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "three_wise_records"

    def _col(self):
        return self._client.collection(self._collection)

    def create(self, record: ThreeWiseRecord) -> ThreeWiseRecord:
        self._col().document(record.id).set(record.model_dump())
        return record

    def get(self, tenant_id: str, env: str, record_id: str) -> Optional[ThreeWiseRecord]:
        snap = self._col().document(record_id).get()
        if snap and snap.exists:
            data = snap.to_dict()
            if data.get("tenant_id") == tenant_id and data.get("env") == env:
                return ThreeWiseRecord(**data)
        return None

    def list(self, tenant_id: str, env: str) -> List[ThreeWiseRecord]:
        query = self._col().where("tenant_id", "==", tenant_id).where("env", "==", env)
        return [ThreeWiseRecord(**d.to_dict()) for d in query.stream()]

    def update(self, record: ThreeWiseRecord) -> ThreeWiseRecord:
        self._col().document(record.id).set(record.model_dump())
        return record
