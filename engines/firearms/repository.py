from __future__ import annotations

import os
from typing import Dict, List, Optional, Protocol

from engines.firearms.models import FirearmsLicence, LicenceLevel, LicenceStatus


class FirearmsRepository(Protocol):
    def issue(self, licence: FirearmsLicence) -> FirearmsLicence: ...
    def get(self, tenant_id: str, env: str, licence_id: str) -> Optional[FirearmsLicence]: ...
    def list(
        self,
        tenant_id: str,
        env: str,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        status: Optional[LicenceStatus] = None,
        level: Optional[LicenceLevel] = None,
    ) -> List[FirearmsLicence]: ...
    def update(self, licence: FirearmsLicence) -> FirearmsLicence: ...


class InMemoryFirearmsRepository:
    def __init__(self) -> None:
        self._items: Dict[tuple[str, str, str], FirearmsLicence] = {}

    def issue(self, licence: FirearmsLicence) -> FirearmsLicence:
        self._items[(licence.tenant_id, licence.env, licence.id)] = licence
        return licence

    def get(self, tenant_id: str, env: str, licence_id: str) -> Optional[FirearmsLicence]:
        return self._items.get((tenant_id, env, licence_id))

    def list(
        self,
        tenant_id: str,
        env: str,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        status: Optional[LicenceStatus] = None,
        level: Optional[LicenceLevel] = None,
    ) -> List[FirearmsLicence]:
        licences = [l for (t, e, _), l in self._items.items() if t == tenant_id and e == env]
        if subject_type:
            licences = [l for l in licences if l.subject_type == subject_type]
        if subject_id:
            licences = [l for l in licences if l.subject_id == subject_id]
        if status:
            licences = [l for l in licences if l.status == status]
        if level:
            licences = [l for l in licences if l.level == level]
        return licences

    def update(self, licence: FirearmsLicence) -> FirearmsLicence:
        self._items[(licence.tenant_id, licence.env, licence.id)] = licence
        return licence


class FirestoreFirearmsRepository(InMemoryFirearmsRepository):
    """Firestore implementation."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore firearms repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "firearms_licences"

    def _col(self):
        return self._client.collection(self._collection)

    def issue(self, licence: FirearmsLicence) -> FirearmsLicence:
        doc_id = licence.id
        self._col().document(doc_id).set(licence.model_dump())
        return licence

    def get(self, tenant_id: str, env: str, licence_id: str) -> Optional[FirearmsLicence]:
        snap = self._col().document(licence_id).get()
        if snap and snap.exists:
            data = snap.to_dict()
            if data.get("tenant_id") == tenant_id and data.get("env") == env:
                return FirearmsLicence(**data)
        return None

    def list(
        self,
        tenant_id: str,
        env: str,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        status: Optional[LicenceStatus] = None,
        level: Optional[LicenceLevel] = None,
    ) -> List[FirearmsLicence]:
        query = self._col().where("tenant_id", "==", tenant_id).where("env", "==", env)
        if subject_type:
            query = query.where("subject_type", "==", subject_type)
        if subject_id:
            query = query.where("subject_id", "==", subject_id)
        if status:
            query = query.where("status", "==", status)
        if level:
            query = query.where("level", "==", level)
        return [FirearmsLicence(**d.to_dict()) for d in query.stream()]

    def update(self, licence: FirearmsLicence) -> FirearmsLicence:
        self._col().document(licence.id).set(licence.model_dump())
        return licence


def firearms_repo_from_env() -> FirearmsRepository:
    backend = os.getenv("FIREARMS_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreFirearmsRepository()
        except Exception:
            return InMemoryFirearmsRepository()
    return InMemoryFirearmsRepository()
