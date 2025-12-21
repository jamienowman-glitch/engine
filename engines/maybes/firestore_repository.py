"""Firestore-backed MAYBES repository."""
from __future__ import annotations

from typing import List, Optional

from engines.config import runtime_config
from engines.maybes.schemas import MaybeItem, MaybeQuery, MaybeUpdate

try:  # pragma: no cover - optional dependency
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    firestore = None


def _tenant_env_key(tenant_id: str, env: str) -> str:
    return f"{tenant_id}__{env}"


class FirestoreMaybesRepository:
    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dependency
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore MAYBES repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._root_collection = "maybes"

    def _collection(self, tenant_id: str, env: str):
        key = _tenant_env_key(tenant_id, env)
        return self._client.collection(self._root_collection).document(key).collection("items")

    def create(self, item: MaybeItem) -> MaybeItem:
        col = self._collection(item.tenant_id, item.env)
        col.document(item.id).set(item.model_dump())
        return item

    def get(self, tenant_id: str, env: str, item_id: str) -> MaybeItem | None:
        snap = self._collection(tenant_id, env).document(item_id).get()
        if not snap or not snap.exists:
            return None
        data = snap.to_dict() or {}
        if data.get("tenant_id") != tenant_id or data.get("env") != env:
            return None
        return MaybeItem(**data)

    def list(self, query: MaybeQuery) -> List[MaybeItem]:
        col = self._collection(query.tenant_id, query.env)
        q = col
        if query.space:
            q = q.where("space", "==", query.space)
        if query.user_id:
            q = q.where("user_id", "==", query.user_id)
        if query.archived is not None:
            q = q.where("archived", "==", query.archived)
        docs = q.stream()
        items: List[MaybeItem] = []
        for snap in docs:
            data = snap.to_dict() or {}
            if query.pinned_only and not data.get("pinned"):
                continue
            if query.tags_any:
                tags = set(data.get("tags") or [])
                if not tags.intersection(set(query.tags_any)):
                    continue
            if query.search_text:
                haystack = f"{data.get('title','')} {data.get('body','')}".lower()
                if query.search_text.lower() not in haystack:
                    continue
            items.append(MaybeItem(**data))
        items.sort(key=lambda i: i.created_at, reverse=True)
        return items[query.offset : query.offset + query.limit]

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
        self._collection(tenant_id, env).document(item_id).set(item.model_dump())
        return item

    def delete(self, tenant_id: str, env: str, item_id: str) -> bool:
        doc = self._collection(tenant_id, env).document(item_id)
        snap = doc.get()
        if not snap or not snap.exists:
            return False
        doc.delete()
        return True
