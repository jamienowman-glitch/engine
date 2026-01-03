from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.persistence.events import emit_persistence_event
from engines.seo.models import PageSeoConfig
from engines.seo.repository import InMemorySeoRepository, SeoRepository, FirestoreSeoRepository, RoutedSeoRepository


def _default_repo() -> SeoRepository:
    backend = os.getenv("SEO_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreSeoRepository()
        except Exception:
            return RoutedSeoRepository()
    return RoutedSeoRepository()


seo_repo: SeoRepository = _default_repo()


class SeoService:
    def __init__(self, repo: Optional[SeoRepository] = None) -> None:
        self.repo = repo or seo_repo

    def upsert(self, ctx: RequestContext, cfg: PageSeoConfig) -> PageSeoConfig:
        now = datetime.now(timezone.utc)
        cfg.id = f"{ctx.tenant_id}:{ctx.project_id}:{cfg.surface}:{cfg.page_type}"
        cfg.tenant_id = ctx.tenant_id
        cfg.env = ctx.env
        cfg.mode = ctx.mode
        cfg.project_id = ctx.project_id
        cfg.surface = cfg.surface or (ctx.surface_id or "")
        cfg.updated_at = now
        if not cfg.created_at:
            cfg.created_at = now
        saved = self.repo.upsert(ctx, cfg)
        emit_persistence_event(
            ctx,
            resource="seo_config",
            action="upsert",
            record_id=saved.id,
            version=saved.version,
        )
        return saved

    def get(self, ctx: RequestContext, surface: str, page_type: str) -> PageSeoConfig | None:
        return self.repo.get(ctx, surface, page_type)

    def list(self, ctx: RequestContext, surface: Optional[str] = None) -> List[PageSeoConfig]:
        return self.repo.list(ctx, surface=surface)


_default_service: Optional[SeoService] = None


def get_seo_service() -> SeoService:
    global _default_service
    if _default_service is None:
        _default_service = SeoService()
    return _default_service


def set_seo_service(service: SeoService) -> None:
    global _default_service, seo_repo
    _default_service = service
    seo_repo = service.repo
