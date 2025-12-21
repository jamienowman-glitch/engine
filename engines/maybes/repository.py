"""Storage abstractions for MAYBES items."""
from __future__ import annotations

import os
from typing import Dict, List, Protocol, Tuple

from engines.maybes.schemas import MaybeItem, MaybeQuery, MaybeUpdate


class MaybesRepository(Protocol):
    def create(self, item: MaybeItem) -> MaybeItem:
        ...

    def get(self, tenant_id: str, env: str, item_id: str) -> MaybeItem | None:
        ...

    def list(self, query: MaybeQuery) -> List[MaybeItem]:
        ...

    def update(self, tenant_id: str, env: str, item_id: str, patch: MaybeUpdate) -> MaybeItem | None:
        ...

    def delete(self, tenant_id: str, env: str, item_id: str) -> bool:
        ...


class InMemoryMaybesRepository:
    """Simple in-memory repository keyed by (tenant_id, env, id)."""

    def __init__(self) -> None:
        self._items: Dict[Tuple[str, str, str], MaybeItem] = {}

    def create(self, item: MaybeItem) -> MaybeItem:
        self._items[(item.tenant_id, item.env, item.id)] = item
        return item

    def get(self, tenant_id: str, env: str, item_id: str) -> MaybeItem | None:
        return self._items.get((tenant_id, env, item_id))

    def list(self, query: MaybeQuery) -> List[MaybeItem]:
        results: List[MaybeItem] = []
        for (t, e, _), item in self._items.items():
            if t != query.tenant_id or e != query.env:
                continue
            if query.space and item.space != query.space:
                continue
            if query.user_id and item.user_id != query.user_id:
                continue
            if query.archived is not None and item.archived != query.archived:
                continue
            if query.pinned_only and not item.pinned:
                continue
            if query.tags_any:
                if not set(query.tags_any).intersection(set(item.tags)):
                    continue
            if query.search_text:
                haystack = f"{item.title} {item.body}".lower()
                if query.search_text.lower() not in haystack:
                    continue
            results.append(item)
        # stable ordering: newest first
        results.sort(key=lambda i: i.created_at, reverse=True)
        start = query.offset
        end = start + query.limit
        return results[start:end]

    def update(self, tenant_id: str, env: str, item_id: str, patch: MaybeUpdate) -> MaybeItem | None:
        item = self.get(tenant_id, env, item_id)
        if not item:
            return None
        if patch.title is not None:
            item.title = patch.title
        if patch.body is not None:
            item.body = patch.body
        if patch.tags is not None:
            item.tags = list(patch.tags)
        if patch.pinned is not None:
            item.pinned = patch.pinned
        if patch.archived is not None:
            item.archived = patch.archived
        self._items[(tenant_id, env, item_id)] = item
        return item

    def delete(self, tenant_id: str, env: str, item_id: str) -> bool:
        return self._items.pop((tenant_id, env, item_id), None) is not None


def maybes_repo_from_env() -> MaybesRepository:
    backend = os.getenv("MAYBES_BACKEND", "").lower()
    if backend == "firestore":
        try:
            from engines.maybes.firestore_repository import FirestoreMaybesRepository

            return FirestoreMaybesRepository()
        except Exception:
            return InMemoryMaybesRepository()
    return InMemoryMaybesRepository()
