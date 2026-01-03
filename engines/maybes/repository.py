"""Storage abstractions for Notes (Maybes) using routed tabular store."""
from __future__ import annotations

from typing import List, Protocol

from engines.common.identity import RequestContext
from engines.maybes.schemas import MaybeItem, MaybeQuery, MaybeUpdate
from engines.storage.versioned_store import ScopeConfig, VersionedStore


class MaybesRepository(Protocol):
    def create(self, context: RequestContext, item: MaybeItem) -> MaybeItem: ...
    def get(self, context: RequestContext, item_id: str) -> MaybeItem | None: ...
    def list(self, context: RequestContext, query: MaybeQuery) -> List[MaybeItem]: ...
    def update(self, context: RequestContext, item_id: str, patch: MaybeUpdate) -> MaybeItem | None: ...
    def delete(self, context: RequestContext, item_id: str) -> int | None: ...


class RoutedMaybesRepository:
    """Persistent repository backed by routed notes_store."""

    def __init__(self) -> None:
        self._scope_cfg = ScopeConfig(include_surface=True, include_app=False, include_user=True)

    def _store(self, context: RequestContext) -> VersionedStore:
        return VersionedStore(
            context,
            resource_kind="notes_store",
            table_name="notes_store",
            scope_config=self._scope_cfg,
        )

    def _to_item(self, record: dict) -> MaybeItem:
        # VersionedStore stores timestamps as ISO strings; coerce via MaybeItem for typing.
        return MaybeItem(**record)

    def create(self, context: RequestContext, item: MaybeItem) -> MaybeItem:
        store = self._store(context)
        record = {
            "tenant_id": item.tenant_id,
            "mode": item.mode,
            "env": item.env,
            "project_id": item.project_id,
            "surface_id": item.surface_id,
            "user_id": item.user_id,
            "title": item.title,
            "content": item.content,
            "tags": item.tags,
            "source": item.source.model_dump(),
            "timestamps": item.timestamps.model_dump(mode="json"),
            "version": item.version,
            "deleted": item.deleted,
        }
        saved = store.save_new(item.note_id, record, user_id=item.user_id, surface_id=item.surface_id)
        return self._to_item(saved)

    def get(self, context: RequestContext, item_id: str) -> MaybeItem | None:
        store = self._store(context)
        record = store.get_latest(item_id, user_id=context.user_id, surface_id=context.surface_id)
        return self._to_item(record) if record and not record.get("deleted") else None

    def list(self, context: RequestContext, query: MaybeQuery) -> List[MaybeItem]:
        store = self._store(context)
        records = store.list_latest(
            user_id=context.user_id,
            surface_id=query.surface_id or context.surface_id,
            include_deleted=False,
        )
        records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        if query.tags_any:
            allowed = set(query.tags_any)
            records = [r for r in records if allowed.intersection(set(r.get("tags", [])))]
        start = query.offset
        end = start + query.limit
        return [self._to_item(r) for r in records[start:end]]

    def update(self, context: RequestContext, item_id: str, patch: MaybeUpdate) -> MaybeItem | None:
        store = self._store(context)
        latest = store.get_latest(item_id, user_id=context.user_id, surface_id=context.surface_id)
        if not latest or latest.get("deleted"):
            return None
        payload = {
            "title": patch.title if patch.title is not None else latest.get("title"),
            "content": patch.content if patch.content is not None else latest.get("content"),
            "tags": patch.tags if patch.tags is not None else latest.get("tags", []),
            "source": patch.source.model_dump() if patch.source is not None else latest.get("source"),
            "surface_id": latest.get("surface_id"),
            "user_id": latest.get("user_id"),
        }
        saved = store.bump_version(item_id, payload, user_id=context.user_id, surface_id=context.surface_id, deleted=False)
        return self._to_item(saved)

    def delete(self, context: RequestContext, item_id: str) -> int | None:
        store = self._store(context)
        latest = store.get_latest(item_id, user_id=context.user_id, surface_id=context.surface_id)
        if not latest:
            return None
        tombstone = store.delete(item_id, user_id=context.user_id, surface_id=context.surface_id)
        return int(tombstone.get("version", 0)) if tombstone else None


def maybes_repo_from_env() -> MaybesRepository:
    # Routing is mandatory; no in-memory fallback.
    return RoutedMaybesRepository()
