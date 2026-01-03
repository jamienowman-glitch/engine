"""Service layer for Notes / Maybes (durable, routed)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional

from engines.common.identity import RequestContext
from engines.maybes.repository import MaybesRepository, maybes_repo_from_env
from engines.maybes.schemas import MaybeCreate, MaybeItem, MaybeQuery, MaybeUpdate, NoteSource, NoteTimestamps
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.persistence.events import emit_persistence_event


class MaybesError(Exception):
    """Base MAYBES error."""


class MaybesNotFound(MaybesError):
    """Raised when an item is missing or tenant/env mismatch occurs."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MaybesService:
    def __init__(
        self,
        repository: Optional[MaybesRepository] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._repo = repository or maybes_repo_from_env()
        self._clock = clock or _utc_now
        self._gate_chain = get_gate_chain()

    def create_item(self, req: MaybeCreate, context: RequestContext) -> MaybeItem:
        if not context.user_id:
            raise MaybesError("user_id is required for notes")
        surface_id = req.surface_id or context.surface_id
        if req.surface_id and context.surface_id and req.surface_id != context.surface_id:
            raise MaybesError("surface_id mismatch with context")
        if not surface_id:
            raise MaybesError("surface_id required")
        project_id = req.project_id or context.project_id
        if req.project_id and req.project_id != context.project_id:
            raise MaybesError("project_id mismatch with context")
        self._gate_chain.run(
            context,
            action="maybes_create",
            surface="maybes",
            subject_type="maybe_item",
        )
        item = MaybeItem(
            tenant_id=context.tenant_id,
            mode=context.mode or context.env or "lab",
            env=context.env,
            project_id=project_id,
            surface_id=surface_id,
            user_id=context.user_id,
            title=req.title,
            content=req.content,
            tags=req.tags,
            source=req.source or NoteSource(created_by="user"),
            timestamps=NoteTimestamps(created_at=self._clock(), updated_at=self._clock()),
        )
        created = self._repo.create(context, item)
        emit_persistence_event(
            context,
            resource="notes",
            action="create",
            record_id=created.note_id,
            version=created.version,
        )
        return created

    def get_item(self, context: RequestContext, item_id: str) -> MaybeItem:
        item = self._repo.get(context, item_id)
        if not item:
            raise MaybesNotFound(f"item {item_id} not found")
        return item

    def list_items(self, context: RequestContext, query: MaybeQuery) -> List[MaybeItem]:
        if query.user_id and query.user_id != context.user_id:
            raise MaybesError("user_id mismatch with context")
        if query.project_id and query.project_id != context.project_id:
            raise MaybesError("project_id mismatch with context")
        if query.surface_id and context.surface_id and query.surface_id != context.surface_id:
            raise MaybesError("surface_id mismatch with context")
        return self._repo.list(context, query)

    def update_item(self, context: RequestContext, item_id: str, patch: MaybeUpdate) -> MaybeItem:
        if not context.user_id:
            raise MaybesError("user_id is required for notes")
        self._gate_chain.run(
            context,
            action="maybes_update",
            surface="maybes",
            subject_type="maybe_item",
            subject_id=item_id,
        )
        item = self._repo.update(context, item_id, patch)
        if not item:
            raise MaybesNotFound(f"item {item_id} not found")
        item.timestamps.updated_at = self._clock()
        emit_persistence_event(
            context,
            resource="notes",
            action="update",
            record_id=item_id,
            version=item.version,
        )
        return item

    def delete_item(self, context: RequestContext, item_id: str) -> None:
        self._gate_chain.run(
            context,
            action="maybes_delete",
            surface="maybes",
            subject_type="maybe_item",
            subject_id=item_id,
        )
        deleted_version = self._repo.delete(context, item_id)
        if deleted_version is None:
            raise MaybesNotFound(f"item {item_id} not found")
        emit_persistence_event(
            context,
            resource="notes",
            action="delete",
            record_id=item_id,
            version=deleted_version,
        )
