from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.seo.models import PageSeoConfig


class SeoRepository(Protocol):
    def upsert(self, cfg: PageSeoConfig) -> PageSeoConfig: ...
    def get(self, tenant_id: str, env: str, surface: str, page_type: str) -> Optional[PageSeoConfig]: ...
    def list(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[PageSeoConfig]: ...


class InMemorySeoRepository:
    def __init__(self) -> None:
        self._items: Dict[tuple[str, str, str, str], PageSeoConfig] = {}

    def upsert(self, cfg: PageSeoConfig) -> PageSeoConfig:
        key = (cfg.tenant_id, cfg.env, cfg.surface, cfg.page_type)
        self._items[key] = cfg
        return cfg

    def get(self, tenant_id: str, env: str, surface: str, page_type: str) -> Optional[PageSeoConfig]:
        return self._items.get((tenant_id, env, surface, page_type))

    def list(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[PageSeoConfig]:
        items = [cfg for (t, e, _, _), cfg in self._items.items() if t == tenant_id and e == env]
        if surface:
            items = [cfg for cfg in items if cfg.surface == surface]
        return items


class FirestoreSeoRepository(InMemorySeoRepository):
    """Firestore implementation for PageSeoConfig."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dep
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore SEO repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "seo_page_configs"

    def _col(self):
        return self._client.collection(self._collection)

    def upsert(self, cfg: PageSeoConfig) -> PageSeoConfig:
        doc_id = f"{cfg.tenant_id}_{cfg.env}_{cfg.surface}_{cfg.page_type}"
        self._col().document(doc_id).set(cfg.model_dump())
        return cfg

    def get(self, tenant_id: str, env: str, surface: str, page_type: str) -> Optional[PageSeoConfig]:
        doc_id = f"{tenant_id}_{env}_{surface}_{page_type}"
        snap = self._col().document(doc_id).get()
        return PageSeoConfig(**snap.to_dict()) if snap and snap.exists else None

    def list(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[PageSeoConfig]:
        query = self._col().where("tenant_id", "==", tenant_id).where("env", "==", env)
        if surface:
            query = query.where("surface", "==", surface)
        return [PageSeoConfig(**d.to_dict()) for d in query.stream()]
