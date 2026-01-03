from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.common.identity import RequestContext
from engines.storage.versioned_store import ScopeConfig, VersionedStore
from engines.seo.models import PageSeoConfig


class SeoRepository(Protocol):
    def upsert(self, context: RequestContext, cfg: PageSeoConfig) -> PageSeoConfig: ...
    def get(self, context: RequestContext, surface: str, page_type: str) -> Optional[PageSeoConfig]: ...
    def list(self, context: RequestContext, surface: Optional[str] = None) -> List[PageSeoConfig]: ...


class InMemorySeoRepository:
    def __init__(self) -> None:
        self._items: Dict[tuple[str, str, str, str], PageSeoConfig] = {}

    def upsert(self, context: RequestContext, cfg: PageSeoConfig) -> PageSeoConfig:
        key = (cfg.tenant_id, cfg.env, cfg.surface, cfg.page_type)
        self._items[key] = cfg
        return cfg

    def get(self, context: RequestContext, surface: str, page_type: str) -> Optional[PageSeoConfig]:
        return self._items.get((context.tenant_id, context.env, surface, page_type))

    def list(self, context: RequestContext, surface: Optional[str] = None) -> List[PageSeoConfig]:
        items = [cfg for (t, e, _, _), cfg in self._items.items() if t == context.tenant_id and e == context.env]
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

    def upsert(self, context: RequestContext, cfg: PageSeoConfig) -> PageSeoConfig:
        doc_id = f"{cfg.tenant_id}_{cfg.env}_{cfg.surface}_{cfg.page_type}"
        self._col().document(doc_id).set(cfg.model_dump())
        return cfg

    def get(self, context: RequestContext, surface: str, page_type: str) -> Optional[PageSeoConfig]:
        doc_id = f"{context.tenant_id}_{context.env}_{surface}_{page_type}"
        snap = self._col().document(doc_id).get()
        return PageSeoConfig(**snap.to_dict()) if snap and snap.exists else None

    def list(self, context: RequestContext, surface: Optional[str] = None) -> List[PageSeoConfig]:
        query = self._col().where("tenant_id", "==", context.tenant_id).where("env", "==", context.env)
        if surface:
            query = query.where("surface", "==", surface)
        return [PageSeoConfig(**d.to_dict()) for d in query.stream()]


class RoutedSeoRepository(InMemorySeoRepository):
    """Versioned, routed persistence via seo_config_store."""

    def __init__(self) -> None:
        self._scope_cfg = ScopeConfig(include_surface=True, include_app=False, include_user=False)

    def _store(self, context: RequestContext) -> VersionedStore:
        return VersionedStore(
            context,
            resource_kind="seo_config_store",
            table_name="seo_config_store",
            scope_config=self._scope_cfg,
        )

    @staticmethod
    def _to_model(record: dict) -> PageSeoConfig:
        return PageSeoConfig(**record)

    def upsert(self, context: RequestContext, cfg: PageSeoConfig) -> PageSeoConfig:
        store = self._store(context)
        payload = cfg.model_dump(mode="json")
        payload["mode"] = context.mode
        existing = store.get_latest(cfg.id, user_id=None, surface_id=cfg.surface)
        if existing:
            saved = store.bump_version(cfg.id, payload, user_id=None, surface_id=cfg.surface, deleted=False)
        else:
            saved = store.save_new(cfg.id, payload, user_id=None, surface_id=cfg.surface)
        return self._to_model(saved)

    def get(self, context: RequestContext, surface: str, page_type: str) -> Optional[PageSeoConfig]:
        store = self._store(context)
        # keys scoped by id; use list to find matching page_type
        records = store.list_latest(user_id=None, surface_id=surface, include_deleted=False)
        for record in records:
            if record.get("page_type") == page_type:
                return self._to_model(record)
        return None

    def list(self, context: RequestContext, surface: Optional[str] = None) -> List[PageSeoConfig]:
        store = self._store(context)
        records = store.list_latest(user_id=None, surface_id=surface or context.surface_id, include_deleted=False)
        return [self._to_model(r) for r in records]
