from __future__ import annotations

from typing import Optional

from engines.common.identity import RequestContext
from engines.memory.models import Blackboard, MessageRecord
from engines.memory.repository import MemoryRepository, memory_repo_from_env


class MemoryService:
    def __init__(self, repo: Optional[MemoryRepository] = None) -> None:
        self.repo = repo or memory_repo_from_env()

    # Session memory
    def append_message(self, ctx: RequestContext, session_id: str, message: MessageRecord) -> dict:
        if not ctx.user_id:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="user_id required for session memory")
        session = self.repo.append_message(ctx.tenant_id, ctx.env, ctx.user_id, session_id, message)
        return session

    def get_session_memory(self, ctx: RequestContext, session_id: str) -> dict:
        if not ctx.user_id:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="user_id required for session memory")
        return self.repo.get_session(ctx.tenant_id, ctx.env, ctx.user_id, session_id) or {}

    # Blackboard
    def write_blackboard(self, ctx: RequestContext, key: str, board: Blackboard) -> Blackboard:
        board.tenant_id = ctx.tenant_id
        board.env = ctx.env
        board.key = key
        return self.repo.write_blackboard(board)

    def read_blackboard(self, ctx: RequestContext, key: str) -> dict:
        board = self.repo.get_blackboard(ctx.tenant_id, ctx.env, key)
        return board or {}

    def clear_blackboard(self, ctx: RequestContext, key: str) -> None:
        self.repo.delete_blackboard(ctx.tenant_id, ctx.env, key)


_default_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _default_service
    if _default_service is None:
        _default_service = MemoryService()
    return _default_service


def set_memory_service(service: MemoryService) -> None:
    global _default_service
    _default_service = service
