"""Training/export privacy preferences (tenant/user opt-out)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Protocol

from engines.config import runtime_config

try:  # pragma: no cover - optional dependency
    from google.cloud import firestore  # type: ignore
except Exception:
    firestore = None


def _doc_id(tenant_id: str, env: str, user_id: Optional[str]) -> str:
    user_part = user_id if user_id else "__tenant"
    return f"{tenant_id}__{env}__{user_part}"



@dataclass
class TrainingPreference:
    tenant_id: str
    env: str
    user_id: Optional[str]
    opt_out: bool


class TrainingPreferenceRepository(Protocol):
    def set_preference(self, pref: TrainingPreference) -> TrainingPreference: ...
    def get_preference(self, tenant_id: str, env: str, user_id: Optional[str]) -> Optional[TrainingPreference]: ...
    def list_preferences(self, tenant_id: str, env: str) -> list[TrainingPreference]: ...


class InMemoryTrainingPreferenceRepository:
    def __init__(self) -> None:
        self._prefs: Dict[tuple[str, str, Optional[str]], TrainingPreference] = {}

    def set_preference(self, pref: TrainingPreference) -> TrainingPreference:
        self._prefs[(pref.tenant_id, pref.env, pref.user_id)] = pref
        return pref

    def get_preference(self, tenant_id: str, env: str, user_id: Optional[str]) -> Optional[TrainingPreference]:
        return self._prefs.get((tenant_id, env, user_id))

    def list_preferences(self, tenant_id: str, env: str) -> list[TrainingPreference]:
        return [p for (t, e, _), p in self._prefs.items() if t == tenant_id and e == env]


class FirestoreTrainingPreferenceRepository:
    _collection_name = "training_preferences"

    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for privacy prefs persistence")
        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for privacy preferences Firestore backend")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _doc(self, tenant_id: str, env: str, user_id: Optional[str]):
        doc_id = _doc_id(tenant_id, env, user_id)
        return self._client.collection(self._collection_name).document(doc_id)

    def set_preference(self, pref: TrainingPreference) -> TrainingPreference:
        self._doc(pref.tenant_id, pref.env, pref.user_id).set(
            {
                "tenant_id": pref.tenant_id,
                "env": pref.env,
                "user_id": pref.user_id,
                "opt_out": pref.opt_out,
            }
        )
        return pref

    def get_preference(self, tenant_id: str, env: str, user_id: Optional[str]) -> Optional[TrainingPreference]:
        snap = self._doc(tenant_id, env, user_id).get()
        if not snap or not getattr(snap, "exists", False):
            return None
        data = snap.to_dict() or {}
        if not data:
            return None
        return TrainingPreference(
            tenant_id=data.get("tenant_id", tenant_id),
            env=data.get("env", env),
            user_id=data.get("user_id"),
            opt_out=data.get("opt_out", False),
        )

    def list_preferences(self, tenant_id: str, env: str) -> list[TrainingPreference]:
        query = (
            self._client.collection(self._collection_name)
            .where("tenant_id", "==", tenant_id)
            .where("env", "==", env)
        )
        results = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            if not data:
                continue
            results.append(
                TrainingPreference(
                    tenant_id=data.get("tenant_id", tenant_id),
                    env=data.get("env", env),
                    user_id=data.get("user_id"),
                    opt_out=data.get("opt_out", False),
                )
            )
        return results


class TrainingPreferenceService:
    def __init__(self, repo: Optional[TrainingPreferenceRepository] = None) -> None:
        self.repo = repo or self._default_repo()

    def _default_repo(self) -> TrainingPreferenceRepository:
        backend = (os.getenv("PRIVACY_BACKEND") or "").lower()
        if backend == "firestore":
            try:
                return FirestoreTrainingPreferenceRepository()
            except Exception:
                pass
        return InMemoryTrainingPreferenceRepository()

    def set_tenant_opt_out(self, tenant_id: str, env: str, opt_out: bool) -> TrainingPreference:
        return self.repo.set_preference(TrainingPreference(tenant_id=tenant_id, env=env, user_id=None, opt_out=opt_out))

    def set_user_opt_out(self, tenant_id: str, env: str, user_id: str, opt_out: bool) -> TrainingPreference:
        return self.repo.set_preference(TrainingPreference(tenant_id=tenant_id, env=env, user_id=user_id, opt_out=opt_out))

    def train_ok(self, tenant_id: str, env: str, user_id: Optional[str], default_ok: bool = True) -> bool:
        # User preference overrides tenant preference when present.
        user_pref = self.repo.get_preference(tenant_id, env, user_id) if user_id else None
        if user_pref is not None:
            return default_ok and (not user_pref.opt_out)
        tenant_pref = self.repo.get_preference(tenant_id, env, None)
        if tenant_pref is not None and tenant_pref.opt_out:
            return False
        return default_ok

    def prefs_snapshot(self, tenant_id: str, env: str) -> list[TrainingPreference]:
        try:
            return self.repo.list_preferences(tenant_id, env)
        except Exception:
            return []


_default_service: Optional[TrainingPreferenceService] = None


def get_training_pref_service() -> TrainingPreferenceService:
    global _default_service
    if _default_service is None:
        _default_service = TrainingPreferenceService()
    return _default_service


def set_training_pref_service(service: TrainingPreferenceService) -> None:
    global _default_service
    _default_service = service
