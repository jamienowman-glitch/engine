"""Repositories for vector corpus items."""
from __future__ import annotations

from typing import Any, Iterable, List, Protocol

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover - optional dep
    firestore = None

from engines.nexus.vector_explorer.schemas import VectorExplorerItem


class VectorCorpusRepository(Protocol):
    def get(self, tenant_id: str, env: str, item_id: str) -> VectorExplorerItem | None:
        ...

    def list_filtered(
        self,
        tenant_id: str,
        env: str,
        space: str,
        tags: list[str] | None = None,
        metadata_filters: dict | None = None,
        limit: int = 20,
    ) -> Iterable[VectorExplorerItem]:
        ...

    def write_record(self, tenant_id: str, record: dict) -> None:
        ...


class InMemoryVectorCorpusRepository:
    def __init__(self, items: list[VectorExplorerItem] | None = None) -> None:
        self._items = {item.id: item for item in (items or [])}

    def get(self, tenant_id: str, env: str, item_id: str) -> VectorExplorerItem | None:
        # tenant/env retained for interface parity; isolation enforced by caller
        return self._items.get(item_id)

    def list_filtered(
        self,
        tenant_id: str,
        env: str,
        space: str,
        tags: list[str] | None = None,
        metadata_filters: dict | None = None,
        limit: int = 20,
    ) -> Iterable[VectorExplorerItem]:
        tags = tags or []
        metadata_filters = metadata_filters or {}
        results: List[VectorExplorerItem] = []
        for item in self._items.values():
            if len(results) >= limit:
                break
            if tags and not set(tags).issubset(set(item.tags)):
                continue
            if metadata_filters:
                # Only perform equality matches on top-level keys stored in metrics/source_ref
                if not _metadata_matches(item, metadata_filters):
                    continue
            results.append(item)
        return results

    def write_record(self, tenant_id: str, record: dict) -> None:
        item = _item_from_doc(record)
        if item:
            self._items[item.id] = item


class FirestoreVectorCorpusRepository:
    def __init__(self, client: Any = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        self._client = client or self._default_client()

    def _default_client(self):
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP_PROJECT_ID/GCP_PROJECT is required for Firestore corpus repository")
        return firestore.Client(project=project)  # type: ignore[arg-type]

    def _collection(self, tenant_id: str):
        if not tenant_id:
            raise RuntimeError("tenant_id is required for vector corpus operations")
        return self._client.collection(f"vector_corpus_{tenant_id}")

    def get(self, tenant_id: str, env: str, item_id: str) -> VectorExplorerItem | None:
        col = self._collection(tenant_id or self._tenant)
        snap = col.document(item_id).get()
        if not snap or not snap.exists:
            return None
        data = snap.to_dict() or {}
        if data.get("env") and data.get("env") != env:
            return None
        return _item_from_doc(data)

    def list_filtered(
        self,
        tenant_id: str,
        env: str,
        space: str,
        tags: list[str] | None = None,
        metadata_filters: dict | None = None,
        limit: int = 20,
    ) -> Iterable[VectorExplorerItem]:
        col = self._collection(tenant_id)
        query = col.where("env", "==", env).where("space", "==", space)
        if tags:
            query = query.where("tags", "array_contains_any", tags)
        docs = query.limit(limit).stream()
        results: List[VectorExplorerItem] = []
        for snap in docs:
            data = snap.to_dict() or {}
            if metadata_filters and not _metadata_matches_raw(data, metadata_filters):
                continue
            item = _item_from_doc(data)
            if item:
                results.append(item)
        return results

    def write_record(self, tenant_id: str, record: dict) -> None:
        col = self._collection(tenant_id)
        col.document(record.get("id")).set(record)


def _item_from_doc(data: dict) -> VectorExplorerItem | None:
    if not data:
        return None
    try:
        return VectorExplorerItem(
            id=data.get("id") or data.get("doc_id") or "",
            label=data.get("label") or data.get("title") or "",
            tags=data.get("tags", []) or [],
            metrics=data.get("metrics", {}) or {},
            similarity_score=None,
            source_ref=data.get("source_ref", {}) or {},
            vector_ref=data.get("vector_ref"),
        )
    except Exception:
        return None


def _metadata_matches(item: VectorExplorerItem, filters: dict) -> bool:
    for key, value in filters.items():
        if key in item.metrics and item.metrics.get(key) != value:
            return False
        if key in item.source_ref and item.source_ref.get(key) != value:
            return False
    return True


def _metadata_matches_raw(data: dict, filters: dict) -> bool:
    metrics = data.get("metrics", {}) or {}
    source_ref = data.get("source_ref", {}) or {}
    for key, value in filters.items():
        if key in metrics and metrics.get(key) != value:
            return False
        if key in source_ref and source_ref.get(key) != value:
            return False
    return True
