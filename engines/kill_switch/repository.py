from __future__ import annotations

from typing import Dict, Optional, Protocol

from engines.kill_switch.models import KillSwitch


class KillSwitchRepository(Protocol):
    def upsert(self, ks: KillSwitch) -> KillSwitch: ...
    def get(self, tenant_id: str, env: str) -> Optional[KillSwitch]: ...


class InMemoryKillSwitchRepository:
    def __init__(self) -> None:
        self._items: Dict[tuple[str, str], KillSwitch] = {}

    def upsert(self, ks: KillSwitch) -> KillSwitch:
        self._items[(ks.tenant_id, ks.env)] = ks
        return ks

    def get(self, tenant_id: str, env: str) -> Optional[KillSwitch]:
        return self._items.get((tenant_id, env))


class FirestoreKillSwitchRepository(InMemoryKillSwitchRepository):
    """Firestore-backed repository."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore kill switch repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "kill_switches"

    def _col(self):
        return self._client.collection(self._collection)

    def upsert(self, ks: KillSwitch) -> KillSwitch:
        self._col().document(f"{ks.tenant_id}_{ks.env}").set(ks.model_dump())
        return ks

    def get(self, tenant_id: str, env: str) -> Optional[KillSwitch]:
        doc = self._col().document(f"{tenant_id}_{env}").get()
        if doc and doc.exists:
            return KillSwitch(**doc.to_dict())
        return None
