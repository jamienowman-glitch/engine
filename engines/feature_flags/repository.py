from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from engines.config import runtime_config
from engines.feature_flags.models import FeatureFlags

FEATURE_FLAGS_BACKEND_ENV = "FEATURE_FLAGS_BACKEND"
GLOBAL_TENANT_ID = "tenant-0"
FEATURE_FLAG_COLLECTION = "feature_flags"
DOC_ID_DELIMITER = "__"


class FirestoreFeatureFlagRepository:
    def __init__(self, client: Optional[Any] = None):
        self._client = client or self._default_client()
        self._collection_name = FEATURE_FLAG_COLLECTION

    def _default_client(self) -> Any:
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "google-cloud-firestore is required for the feature flag backend"
            ) from exc

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore feature flags")
        return firestore.Client(project=project)  # type: ignore[arg-type]

    def _doc(self, tenant_id: str, env: str):
        doc_id = f"{tenant_id}{DOC_ID_DELIMITER}{env}"
        return self._client.collection(self._collection_name).document(doc_id)

    def get_flags(self, tenant_id: str, env: str) -> Optional[FeatureFlags]:
        snap = self._doc(tenant_id, env).get()
        if not snap or not getattr(snap, "exists", False):
            return None
        data = snap.to_dict() or {}
        if not data:
            return None
        return FeatureFlags(**data)

    def set_flags(self, flags: FeatureFlags) -> FeatureFlags:
        self._doc(flags.tenant_id, flags.env).set(flags.model_dump())
        return flags

    def delete_flags(self, tenant_id: str, env: str) -> None:
        self._doc(tenant_id, env).delete()



class InMemoryFeatureFlagRepository:
    def __init__(self):
        self._store: Dict[Tuple[str, str], FeatureFlags] = {}

    def get_flags(self, tenant_id: str, env: str) -> Optional[FeatureFlags]:
        return self._store.get((tenant_id, env))

    def set_flags(self, flags: FeatureFlags) -> FeatureFlags:
        self._store[(flags.tenant_id, flags.env)] = flags
        return flags

    def delete_flags(self, tenant_id: str, env: str) -> None:
        self._store.pop((tenant_id, env), None)


class FeatureFlagRepository:
    def __init__(self, backend: Optional[str] = None, firestore_client: Optional[Any] = None):
        # GAP-G1: No memory fallback. Must use Firestore in production.
        self._firestore_repo: Optional[FirestoreFeatureFlagRepository] = None
        self._memory_repo: Optional[InMemoryFeatureFlagRepository] = None
        self._backend = (backend or os.getenv(FEATURE_FLAGS_BACKEND_ENV, "")).lower()

        # The original code had a try/except block for Firestore initialization.
        # The instruction removes it, so we'll follow the instruction.
        if self._backend == "firestore":
            self._firestore_repo = FirestoreFeatureFlagRepository(client=firestore_client)
        elif self._backend == "memory":
            self._memory_repo = InMemoryFeatureFlagRepository()
        elif not self._backend:
             raise RuntimeError(
                "FEATURE_FLAGS_BACKEND not set. "
                "Set FEATURE_FLAGS_BACKEND=firestore and ensure GCP credentials are available."
            )
        else:
            raise RuntimeError(
                f"Unsupported FEATURE_FLAGS_BACKEND={self._backend}. "
                "Only 'firestore' is allowed in production."
            )

    def get_flags(self, tenant_id: str, env: str) -> Optional[FeatureFlags]:
        if self._memory_repo:
            return self._memory_repo.get_flags(tenant_id, env)
        return self._firestore_repo.get_flags(tenant_id, env) if self._firestore_repo else None

    def set_flags(self, flags: FeatureFlags) -> FeatureFlags:
        if self._memory_repo:
            return self._memory_repo.set_flags(flags)
        if self._firestore_repo:
            self._firestore_repo.set_flags(flags)
        return flags

    def delete_flags(self, tenant_id: str, env: str) -> None:
        if self._memory_repo:
            return self._memory_repo.delete_flags(tenant_id, env)
        if self._firestore_repo:
            self._firestore_repo.delete_flags(tenant_id, env)

    def get_global_flags(self, env: str) -> Optional[FeatureFlags]:
        return self.get_flags(GLOBAL_TENANT_ID, env)


# Global singleton storage
feature_flag_repo = FeatureFlagRepository()
