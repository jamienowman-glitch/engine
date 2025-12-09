"""Firestore backend for Nexus persistence."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover - library may not be installed locally
    firestore = None

from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.nexus.schemas import NexusDocument, NexusKind


class FirestoreNexusBackend:
    """Persist Nexus documents and events in Firestore (native, us-central1)."""

    def __init__(self, client: Any = None) -> None:
        self._client = client or self._default_client()
        cfg = runtime_config.config_snapshot()
        self.tenant_id = cfg["tenant_id"] or ""
        self.env = cfg["env"] or "dev"
        self._plan_cache = {}

    def _default_client(self) -> Any:
        if firestore is None:
            raise RuntimeError(
                "google-cloud-firestore is not installed; cannot use Firestore backend"
            )
        project = runtime_config.get_firestore_project()
        return firestore.Client(project=project)  # type: ignore[arg-type]

    def _collection(self, suffix: str):
        name = f"{suffix}_{self.tenant_id}"
        return self._client.collection(name)

    def write_snippet(
        self, kind: NexusKind, doc: NexusDocument, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        all_tags: List[str] = []
        if tags:
            all_tags.extend(tags)
        if getattr(doc, "tags", None):
            all_tags.extend(doc.tags)
        # ensure tags unique but preserve order
        seen = set()
        deduped_tags = []
        for t in all_tags:
            if t in seen:
                continue
            seen.add(t)
            deduped_tags.append(t)
        payload = {
            "id": doc.id,
            "text": doc.text,
            "kind": kind.value,
            "tenant_id": doc.tenant_id or self.tenant_id,
            "env": doc.env or self.env,
            "tags": deduped_tags,
            "metadata": getattr(doc, "metadata", {}) or {},
            "refs": getattr(doc, "refs", {}) or {},
        }
        self._collection("nexus_snippets").document(doc.id).set(payload)
        return payload

    def write_event(self, event: DatasetEvent) -> Dict[str, Any]:
        payload = event.model_dump()
        self._collection("nexus_events").add(payload)
        return payload

    def get_snippets_by_ids(self, ids: List[str]) -> List[NexusDocument]:
        col = self._collection("nexus_snippets")
        docs = []
        for doc_id in ids:
            snap = col.document(doc_id).get()
            if not snap or not snap.exists:
                continue
            data = snap.to_dict()
            docs.append(
                NexusDocument(
                    id=doc_id,
                    text=data.get("text", ""),
                    tenant_id=data.get("tenant_id", self.tenant_id),
                    env=data.get("env", self.env),
                    kind=NexusKind(data.get("kind", "data")),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                    refs=data.get("refs", {}),
                )
            )
        return docs

    def query_by_tags(
        self, kind: NexusKind, tags: List[str], limit: int = 5
    ) -> List[NexusDocument]:
        col = self._collection("nexus_snippets")
        query = col.where("kind", "==", kind.value)
        if tags:
            query = query.where("tags", "array_contains_any", tags)
        docs = query.limit(limit).stream()
        results: List[NexusDocument] = []
        for d in docs:
            data = d.to_dict()
            results.append(
                NexusDocument(
                    id=d.id,
                    text=data.get("text", ""),
                    tenant_id=data.get("tenant_id", self.tenant_id),
                    env=data.get("env", self.env),
                    kind=kind,
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                    refs=data.get("refs", {}),
                )
            )
        return results

    def query_for_agent(
        self, agent_id: str, limit: int = 5
    ) -> List[DatasetEvent]:
        col = self._collection("nexus_events")
        docs = (
            col.where("agentId", "==", agent_id)
            .order_by("env")
            .limit(limit)
            .stream()
        )
        results: List[DatasetEvent] = []
        for doc in docs:
            try:
                results.append(DatasetEvent(**doc.to_dict()))
            except Exception:
                continue
        return results

    def get_latest_plan(self, kind: str, tenantId: str, env: Optional[str] = None, status: Optional[str] = None) -> Optional[Dict[str, Any]]:
        cache_key = (kind, tenantId, env or self.env, status)
        if cache_key in self._plan_cache:
            return self._plan_cache[cache_key]
        col_name = f"{kind}_plans_{tenantId}"
        col = self._client.collection(col_name)
        query = col.order_by("version", direction=firestore.Query.DESCENDING)  # type: ignore
        if env:
            query = query.where("env", "==", env)
        if status:
            query = query.where("status", "==", status)
        docs = list(query.limit(1).stream())
        if not docs:
            return None
        data = docs[0].to_dict()
        self._plan_cache[cache_key] = data
        return data

    def save_plan(self, kind: str, tenantId: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        col_name = f"{kind}_plans_{tenantId}"
        col = self._client.collection(col_name)
        latest = self.get_latest_plan(kind, tenantId, plan.get("env"), None)
        next_version = (latest.get("version", 0) if latest else 0) + 1
        plan["version"] = plan.get("version", next_version)
        col.add(plan)
        self._plan_cache.clear()
        return plan
