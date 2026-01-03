from __future__ import annotations

from typing import List, Optional, Protocol

from engines.common.identity import RequestContext
from engines.storage.versioned_store import ScopeConfig, VersionedStore
from engines.strategy_lock.models import StrategyLock, StrategyStatus


class StrategyLockRepository(Protocol):
    def create(self, context: RequestContext, lock: StrategyLock) -> StrategyLock: ...
    def get(self, context: RequestContext, lock_id: str) -> Optional[StrategyLock]: ...
    def get_version(self, context: RequestContext, lock_id: str, version: int) -> Optional[StrategyLock]: ...
    def list(
        self,
        context: RequestContext,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]: ...
    def update(self, context: RequestContext, lock: StrategyLock) -> StrategyLock: ...


class InMemoryStrategyLockRepository:
    def __init__(self) -> None:
        self._locks: dict[tuple[str, str, str], StrategyLock] = {}

    def create(self, context: RequestContext, lock: StrategyLock) -> StrategyLock:
        key = (lock.tenant_id, lock.env, lock.id)
        self._locks[key] = lock
        return lock

    def get(self, context: RequestContext, lock_id: str) -> Optional[StrategyLock]:
        return self._locks.get((context.tenant_id, context.env, lock_id))
    
    def get_version(self, context: RequestContext, lock_id: str, version: int) -> Optional[StrategyLock]:
        return self.get(context, lock_id)

    def list(
        self,
        context: RequestContext,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]:
        locks = [l for (t, e, _), l in self._locks.items() if t == context.tenant_id and e == context.env]
        if status:
            locks = [l for l in locks if l.status == status]
        if surface:
            locks = [l for l in locks if l.surface == surface]
        if scope:
            locks = [l for l in locks if l.scope == scope]
        return locks

    def update(self, context: RequestContext, lock: StrategyLock) -> StrategyLock:
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

    def create(self, context: RequestContext, lock: StrategyLock) -> StrategyLock:
        self._col().document(lock.id).set(lock.model_dump())
        return lock

    def get(self, context: RequestContext, lock_id: str) -> Optional[StrategyLock]:
        snap = self._col().document(lock_id).get()
        if snap and snap.exists:
            data = snap.to_dict()
            if data.get("tenant_id") == context.tenant_id and data.get("env") == context.env:
                return StrategyLock(**data)
        return None
    
    def get_version(self, context: RequestContext, lock_id: str, version: int) -> Optional[StrategyLock]:
        return self.get(context, lock_id)

    def list(
        self,
        context: RequestContext,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]:
        query = self._col().where("tenant_id", "==", context.tenant_id).where("env", "==", context.env)
        if status:
            query = query.where("status", "==", status)
        if surface:
            query = query.where("surface", "==", surface)
        if scope:
            query = query.where("scope", "==", scope)
        return [StrategyLock(**d.to_dict()) for d in query.stream()]

    def update(self, context: RequestContext, lock: StrategyLock) -> StrategyLock:
        self._col().document(lock.id).set(lock.model_dump())
        return lock


class RoutedStrategyLockRepository(InMemoryStrategyLockRepository):
    """Versioned, routed persistence via strategy_lock_store."""

    def __init__(self) -> None:
        self._scope_cfg = ScopeConfig(include_surface=True, include_app=True, include_user=True)

    def _store(self, context: RequestContext) -> VersionedStore:
        return VersionedStore(
            context,
            resource_kind="strategy_lock_store",
            table_name="strategy_lock_store",
            scope_config=self._scope_cfg,
        )

    @staticmethod
    def _to_lock(record: dict) -> StrategyLock:
        return StrategyLock(**record)

    def create(self, context: RequestContext, lock: StrategyLock) -> StrategyLock:
        store = self._store(context)
        payload = lock.model_dump(mode="json")
        payload["mode"] = context.mode
        saved = store.save_new(lock.id, payload, user_id=context.user_id, surface_id=lock.surface)
        return self._to_lock(saved)

    def get(self, context: RequestContext, lock_id: str) -> Optional[StrategyLock]:
        store = self._store(context)
        record = store.get_latest(lock_id, user_id=context.user_id, surface_id=context.surface_id)
        return self._to_lock(record) if record and not record.get("deleted") else None
    
    def get_version(self, context: RequestContext, lock_id: str, version: int) -> Optional[StrategyLock]:
        store = self._store(context)
        record = store.get_version(lock_id, version, user_id=context.user_id, surface_id=context.surface_id)
        return self._to_lock(record) if record and not record.get("deleted") else None

    def list(
        self,
        context: RequestContext,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]:
        store = self._store(context)
        records = store.list_latest(user_id=context.user_id, surface_id=surface or context.surface_id, include_deleted=False)
        locks = [self._to_lock(r) for r in records]
        if status:
            locks = [l for l in locks if l.status == status]
        if surface:
            locks = [l for l in locks if l.surface == surface]
        if scope:
            locks = [l for l in locks if l.scope == scope]
        return locks

    def update(self, context: RequestContext, lock: StrategyLock) -> StrategyLock:
        store = self._store(context)
        payload = lock.model_dump(mode="json")
        payload["mode"] = context.mode
        saved = store.bump_version(lock.id, payload, user_id=context.user_id, surface_id=lock.surface, deleted=False)
        return self._to_lock(saved)
