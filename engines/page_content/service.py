from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.page_content.models import PageContent
from engines.page_content.repository import (
    FirestorePageContentRepository,
    InMemoryPageContentRepository,
    PageContentRepository,
)
from engines.strategy_lock.models import ACTION_BUILDER_PUBLISH_PAGE, ACTION_BUILDER_UPDATE_PAGE
from engines.strategy_lock.service import get_strategy_lock_service
from engines.logging.audit import emit_audit_event


def _default_repo() -> PageContentRepository:
    backend = os.getenv("PAGE_CONTENT_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestorePageContentRepository()
        except Exception:
            return InMemoryPageContentRepository()
    return InMemoryPageContentRepository()


page_repo: PageContentRepository = _default_repo()


class PageContentService:
    def __init__(self, repo: Optional[PageContentRepository] = None) -> None:
        self.repo = repo or page_repo
        self._lock_service = get_strategy_lock_service()

    def create_page(self, ctx: RequestContext, page: PageContent) -> PageContent:
        self._lock_service.require_strategy_lock_or_raise(ctx, page.surface, ACTION_BUILDER_UPDATE_PAGE)
        page.tenant_id = ctx.tenant_id
        page.env = ctx.env
        created = self.repo.create(page)
        emit_audit_event(ctx, action="page.create", surface="pages", metadata={"page_id": created.id, "slug": created.slug})
        return created

    def list_pages(self, ctx: RequestContext, surface: Optional[str]) -> List[PageContent]:
        return self.repo.list(ctx.tenant_id, ctx.env, surface=surface)

    def get_page(self, ctx: RequestContext, page_id: str) -> PageContent:
        page = self.repo.get(ctx.tenant_id, ctx.env, page_id)
        if not page:
            raise HTTPException(status_code=404, detail="page_not_found")
        return page

    def update_page(self, ctx: RequestContext, page_id: str, patch: PageContent) -> PageContent:
        page = self.get_page(ctx, page_id)
        self._lock_service.require_strategy_lock_or_raise(ctx, page.surface, ACTION_BUILDER_UPDATE_PAGE)
        if patch.slug:
            page.slug = patch.slug
        if patch.html_or_json:
            page.html_or_json = patch.html_or_json
        page.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update(page)
        emit_audit_event(ctx, action="page.update", surface="pages", metadata={"page_id": page.id, "slug": page.slug})
        return updated

    def publish_page(self, ctx: RequestContext, page_id: str) -> PageContent:
        page = self.get_page(ctx, page_id)
        self._lock_service.require_strategy_lock_or_raise(ctx, page.surface, ACTION_BUILDER_PUBLISH_PAGE)
        page.published = True
        page.published_at = datetime.now(timezone.utc)
        page.updated_at = page.published_at
        updated = self.repo.update(page)
        emit_audit_event(ctx, action="page.publish", surface="pages", metadata={"page_id": page.id, "slug": page.slug})
        return updated

    def delete_page(self, ctx: RequestContext, page_id: str) -> None:
        page = self.get_page(ctx, page_id)
        self._lock_service.require_strategy_lock_or_raise(ctx, page.surface, ACTION_BUILDER_UPDATE_PAGE)
        self.repo.delete(ctx.tenant_id, ctx.env, page_id)
        emit_audit_event(ctx, action="page.delete", surface="pages", metadata={"page_id": page_id})


_default_service: Optional[PageContentService] = None


def get_page_content_service() -> PageContentService:
    global _default_service
    if _default_service is None:
        _default_service = PageContentService()
    return _default_service


def set_page_content_service(service: PageContentService) -> None:
    global _default_service, page_repo
    _default_service = service
    page_repo = service.repo
