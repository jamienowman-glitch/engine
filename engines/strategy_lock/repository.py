from __future__ import annotations

from typing import List, Optional, Protocol

from engines.strategy_lock.models import StrategyLock, StrategyStatus


class StrategyLockRepository(Protocol):
    def create(self, lock: StrategyLock) -> StrategyLock: ...
    def get(self, tenant_id: str, env: str, lock_id: str) -> Optional[StrategyLock]: ...
    def list(
        self,
        tenant_id: str,
        env: str,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]: ...
    def update(self, lock: StrategyLock) -> StrategyLock: ...


class InMemoryStrategyLockRepository:
    def __init__(self) -> None:
        self._locks: dict[tuple[str, str, str], StrategyLock] = {}

    def create(self, lock: StrategyLock) -> StrategyLock:
        key = (lock.tenant_id, lock.env, lock.id)
        self._locks[key] = lock
        return lock

    def get(self, tenant_id: str, env: str, lock_id: str) -> Optional[StrategyLock]:
        return self._locks.get((tenant_id, env, lock_id))

    def list(
        self,
        tenant_id: str,
        env: str,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]:
        locks = [l for (t, e, _), l in self._locks.items() if t == tenant_id and e == env]
        if status:
            locks = [l for l in locks if l.status == status]
        if surface:
            locks = [l for l in locks if l.surface == surface]
        if scope:
            locks = [l for l in locks if l.scope == scope]
        return locks

    def update(self, lock: StrategyLock) -> StrategyLock:
        key = (lock.tenant_id, lock.env, lock.id)
        self._locks[key] = lock
        return lock


class FirestoreStrategyLockRepository(InMemoryStrategyLockRepository):
    """Firestore implementation for strategy locks."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore strategy lock repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "strategy_locks"

    def _col(self):
        return self._client.collection(self._collection)

    def create(self, lock: StrategyLock) -> StrategyLock:
        self._col().document(lock.id).set(lock.model_dump())
        return lock

    def get(self, tenant_id: str, env: str, lock_id: str) -> Optional[StrategyLock]:
        snap = self._col().document(lock_id).get()
        if snap and snap.exists:
            data = snap.to_dict()
            if data.get("tenant_id") == tenant_id and data.get("env") == env:
                return StrategyLock(**data)
        return None

    def list(
        self,
        tenant_id: str,
        env: str,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]:
        query = self._col().where("tenant_id", "==", tenant_id).where("env", "==", env)
        if status:
            query = query.where("status", "==", status)
        if surface:
            query = query.where("surface", "==", surface)
        if scope:
            query = query.where("scope", "==", scope)
        return [StrategyLock(**d.to_dict()) for d in query.stream()]

    def update(self, lock: StrategyLock) -> StrategyLock:
        self._col().document(lock.id).set(lock.model_dump())
        return lock
