"""Firestore-backed repository for Maybes notes."""
from __future__ import annotations

from typing import Any, Iterable, List

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover - library may be absent locally
    firestore = None

from engines.config import runtime_config
from engines.maybes.schemas import MaybesNote
from engines.maybes.repository import MaybesRepository


class FirestoreMaybesRepository(MaybesRepository):
    def __init__(self, client: Any = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        self._client = client or self._default_client()
        cfg = runtime_config.config_snapshot()
        self.tenant_id = cfg.get("tenant_id") or ""
        self.env = cfg.get("env") or "dev"

    def _default_client(self):
        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP_PROJECT_ID/GCP_PROJECT is required for FirestoreMaybesRepository")
        return firestore.Client(project=project)  # type: ignore[arg-type]

    def _collection(self):
        suffix = self.tenant_id or "t_unknown"
        return self._client.collection(f"maybes_notes_{suffix}")

    def save(self, note: MaybesNote) -> MaybesNote:
        payload = note.model_dump()
        payload["tenant_id"] = note.tenant_id or self.tenant_id
        payload["env"] = self.env
        self._collection().document(note.maybes_id).set(payload)
        return note

    def get(self, maybes_id: str) -> MaybesNote | None:
        snap = self._collection().document(maybes_id).get()
        if not snap or not snap.exists:
            return None
        data = snap.to_dict() or {}
        return MaybesNote(**data)

    def list_for_user(self, tenant_id: str, user_id: str) -> Iterable[MaybesNote]:
        query = (
            self._collection()
            .where("tenant_id", "==", tenant_id)
            .where("user_id", "==", user_id)
        )
        docs: List[MaybesNote] = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            try:
                docs.append(MaybesNote(**data))
            except Exception:
                continue
        return docs
