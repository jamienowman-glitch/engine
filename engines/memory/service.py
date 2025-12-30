from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.memory.models import Blackboard, MessageRecord
from engines.memory.repository import MemoryRepository, memory_repo_from_env


def _require_scope(ctx: RequestContext) -> tuple[str, str]:
    if not ctx.user_id:
        raise HTTPException(status_code=400, detail="user_id required for session memory")
    if not ctx.mode:
        raise HTTPException(status_code=400, detail="mode required for session memory")
    if not ctx.project_id:
        raise HTTPException(status_code=400, detail="project_id required for session memory")
    return ctx.mode, ctx.project_id


class MemoryService:
    def __init__(self, repo: Optional[MemoryRepository] = None) -> None:
        self.repo = repo or memory_repo_from_env()

    # Session memory
    def append_message(self, ctx: RequestContext, session_id: str, message: MessageRecord) -> dict:
        mode, project_id = _require_scope(ctx)
        session = self.repo.append_message(
            ctx.tenant_id, mode, project_id, ctx.user_id, session_id, message
        )
        return session

    def get_session_memory(self, ctx: RequestContext, session_id: str) -> dict:
        mode, project_id = _require_scope(ctx)
        return self.repo.get_session(
            ctx.tenant_id, mode, project_id, ctx.user_id, session_id
        ) or {}

    # Blackboard
    def write_blackboard(self, ctx: RequestContext, key: str, board: Blackboard) -> Blackboard:
        mode, project_id = _require_scope(ctx)
        board.tenant_id = ctx.tenant_id
        board.mode = mode
        board.project_id = project_id
        board.key = key
        return self.repo.write_blackboard(board)

    def read_blackboard(self, ctx: RequestContext, key: str) -> dict:
        mode, project_id = _require_scope(ctx)
        board = self.repo.get_blackboard(ctx.tenant_id, mode, project_id, key)
        return board or {}

    def clear_blackboard(self, ctx: RequestContext, key: str) -> None:
        mode, project_id = _require_scope(ctx)
        self.repo.delete_blackboard(ctx.tenant_id, mode, project_id, key)


_default_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _default_service
    if _default_service is None:
        _default_service = MemoryService()
    return _default_service


def set_memory_service(service: MemoryService) -> None:
    global _default_service
    _default_service = service
