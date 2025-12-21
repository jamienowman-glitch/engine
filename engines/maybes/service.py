"""Service layer for MAYBES scratchpad items (in-memory only)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional
from uuid import uuid4

from engines.common.identity import RequestContext
from engines.logging.audit import emit_audit_event
from engines.maybes.repository import InMemoryMaybesRepository, MaybesRepository, maybes_repo_from_env
from engines.maybes.schemas import MaybeCreate, MaybeItem, MaybeQuery, MaybeUpdate
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain


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
        id_fn: Optional[Callable[[], str]] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._repo = repository or maybes_repo_from_env()
        self._id_fn = id_fn or (lambda: uuid4().hex)
        self._clock = clock or _utc_now
        self._gate_chain = get_gate_chain()

    def _assert_context_match(self, req: MaybeCreate, context: RequestContext) -> None:
        if req.tenant_id and req.tenant_id != context.tenant_id:
            raise MaybesError("tenant mismatch")
        if req.env and req.env != context.env:
            raise MaybesError("env mismatch")

    def create_item(self, req: MaybeCreate, context: RequestContext) -> MaybeItem:
        self._assert_context_match(req, context)
        self._gate_chain.run(
            context,
            action="maybes_create",
            surface="maybes",
            subject_type="maybe_item",
        )
        item = MaybeItem(
            id=self._id_fn(),
            tenant_id=context.tenant_id,
            env=context.env,
            space=req.space,
            user_id=req.user_id or context.user_id,
            title=req.title,
            body=req.body,
            tags=req.tags,
            source_type=req.source_type,
            source_engine=req.source_engine,
            source_ref=req.source_ref,
            pinned=req.pinned,
            archived=False,
            created_at=self._clock(),
            updated_at=self._clock(),
        )
        created = self._repo.create(item)
        emit_audit_event(
            context,
            action="maybes:create",
            surface="maybes",
            metadata={"item_id": created.id},
        )
        return created

    def get_item(self, context: RequestContext, item_id: str) -> MaybeItem:
        item = self._repo.get(context.tenant_id, context.env, item_id)
        if not item:
            raise MaybesNotFound(f"item {item_id} not found")
        return item

    def list_items(self, query: MaybeQuery) -> List[MaybeItem]:
        return self._repo.list(query)

    def update_item(self, context: RequestContext, item_id: str, patch: MaybeUpdate) -> MaybeItem:
        self._gate_chain.run(
            context,
            action="maybes_update",
            surface="maybes",
            subject_type="maybe_item",
            subject_id=item_id,
        )
        item = self._repo.update(context.tenant_id, context.env, item_id, patch)
        if not item:
            raise MaybesNotFound(f"item {item_id} not found")
        item.updated_at = self._clock()
        self._repo.create(item)
        emit_audit_event(
            context,
            action="maybes:update",
            surface="maybes",
            metadata={"item_id": item_id},
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
        deleted = self._repo.delete(context.tenant_id, context.env, item_id)
        if not deleted:
            raise MaybesNotFound(f"item {item_id} not found")
        emit_audit_event(
            context,
            action="maybes:delete",
            surface="maybes",
            metadata={"item_id": item_id},
        )
