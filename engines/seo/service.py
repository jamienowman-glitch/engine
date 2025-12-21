from __future__ import annotations

import os
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.seo.models import PageSeoConfig
from engines.seo.repository import InMemorySeoRepository, SeoRepository, FirestoreSeoRepository


def _default_repo() -> SeoRepository:
    backend = os.getenv("SEO_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreSeoRepository()
        except Exception:
            return InMemorySeoRepository()
    return InMemorySeoRepository()


seo_repo: SeoRepository = _default_repo()


class SeoService:
    def __init__(self, repo: Optional[SeoRepository] = None) -> None:
        self.repo = repo or seo_repo

    def upsert(self, ctx: RequestContext, cfg: PageSeoConfig) -> PageSeoConfig:
        cfg.tenant_id = ctx.tenant_id
        cfg.env = ctx.env
        return self.repo.upsert(cfg)

    def get(self, ctx: RequestContext, surface: str, page_type: str) -> PageSeoConfig | None:
        return self.repo.get(ctx.tenant_id, ctx.env, surface, page_type)

    def list(self, ctx: RequestContext, surface: Optional[str] = None) -> List[PageSeoConfig]:
        return self.repo.list(ctx.tenant_id, ctx.env, surface=surface)


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
