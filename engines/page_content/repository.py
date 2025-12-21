from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.page_content.models import PageContent


class PageContentRepository(Protocol):
    def create(self, page: PageContent) -> PageContent: ...
    def get(self, tenant_id: str, env: str, page_id: str) -> Optional[PageContent]: ...
    def list(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[PageContent]: ...
    def update(self, page: PageContent) -> PageContent: ...
    def delete(self, tenant_id: str, env: str, page_id: str) -> None: ...


class InMemoryPageContentRepository:
    def __init__(self) -> None:
        self._items: Dict[tuple[str, str, str], PageContent] = {}

    def create(self, page: PageContent) -> PageContent:
        self._items[(page.tenant_id, page.env, page.id)] = page
        return page

    def get(self, tenant_id: str, env: str, page_id: str) -> Optional[PageContent]:
        return self._items.get((tenant_id, env, page_id))

    def list(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[PageContent]:
        items = [p for (t, e, _), p in self._items.items() if t == tenant_id and e == env]
        if surface:
            items = [p for p in items if p.surface == surface]
        return items

    def update(self, page: PageContent) -> PageContent:
        self._items[(page.tenant_id, page.env, page.id)] = page
        return page

    def delete(self, tenant_id: str, env: str, page_id: str) -> None:
        self._items.pop((tenant_id, env, page_id), None)


class FirestorePageContentRepository(InMemoryPageContentRepository):
    """Firestore implementation."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore page content repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "page_content"

    def _col(self):
        return self._client.collection(self._collection)

    def create(self, page: PageContent) -> PageContent:
        self._col().document(page.id).set(page.model_dump())
        return page

    def get(self, tenant_id: str, env: str, page_id: str) -> Optional[PageContent]:
        snap = self._col().document(page_id).get()
        if snap and snap.exists:
            data = snap.to_dict()
            if data.get("tenant_id") == tenant_id and data.get("env") == env:
                return PageContent(**data)
        return None

    def list(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[PageContent]:
        query = self._col().where("tenant_id", "==", tenant_id).where("env", "==", env)
        if surface:
            query = query.where("surface", "==", surface)
        return [PageContent(**d.to_dict()) for d in query.stream()]

    def update(self, page: PageContent) -> PageContent:
        self._col().document(page.id).set(page.model_dump())
        return page

    def delete(self, tenant_id: str, env: str, page_id: str) -> None:
        snap = self._col().document(page_id).get()
        if snap and snap.exists:
            data = snap.to_dict()
            if data.get("tenant_id") == tenant_id and data.get("env") == env:
                self._col().document(page_id).delete()
