from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.memory.models import Blackboard, MessageRecord
from engines.memory.repository import MemoryRepository, memory_repo_from_env
from engines.memory.cloud_memory_store import (
    FirestoreMemoryStore,
    DynamoDBMemoryStore,
    CosmosMemoryStore,
)


def _require_scope(ctx: RequestContext) -> tuple[str, str]:
    if not ctx.user_id:
        raise HTTPException(status_code=400, detail="user_id required for session memory")
    if not ctx.mode:
        raise HTTPException(status_code=400, detail="mode required for session memory")
    if not ctx.project_id:
        raise HTTPException(status_code=400, detail="project_id required for session memory")
    return ctx.mode, ctx.project_id


class MemoryService:
    def __init__(self, repo: Optional[MemoryRepository] = None, backend_type: Optional[str] = None, config: Optional[dict] = None) -> None:
        """Initialize memory service with optional cloud backend.
        
        Args:
            repo: Traditional in-memory repository (fallback)
            backend_type: Cloud backend type (firestore, dynamodb, cosmos)
            config: Backend configuration dict
        """
        self._backend_type = backend_type
        self._config = config or {}
        
        if backend_type:
            # Use cloud backend (Builder A)
            self._repo = self._resolve_cloud_repo(backend_type, config or {})
        else:
            # Fall back to in-memory (for backward compat and lab)
            self.repo = repo or memory_repo_from_env()
    
    def _resolve_cloud_repo(self, backend_type: str, config: dict):
        """Resolve cloud backend repository."""
        backend_type = (backend_type or "").lower()
        
        if backend_type == "firestore":
            project = config.get("project")
            store = FirestoreMemoryStore(project=project)
            # Wrap cloud store to match repository interface
            return _CloudMemoryRepositoryWrapper(store)
        elif backend_type == "dynamodb":
            table_name = config.get("table_name")
            region = config.get("region", "us-west-2")
            store = DynamoDBMemoryStore(table_name=table_name, region=region)
            return _CloudMemoryRepositoryWrapper(store)
        elif backend_type == "cosmos":
            endpoint = config.get("endpoint")
            key = config.get("key")
            database = config.get("database", "memory_store")
            store = CosmosMemoryStore(endpoint=endpoint, key=key, database=database)
            return _CloudMemoryRepositoryWrapper(store)
        else:
            raise RuntimeError(f"Unsupported memory backend_type={backend_type}")

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

class _CloudMemoryRepositoryWrapper:
    """Adapter to present cloud memory store as MemoryRepository interface."""
    
    def __init__(self, store) -> None:
        self._store = store
    
    def append_message(self, tenant_id: str, mode: str, project_id: str, user_id: str, session_id: str, message: MessageRecord) -> dict:
        from engines.memory.models import SessionMemory
        session = self._store.get_session(tenant_id, mode, project_id, user_id, session_id)
        if not session:
            session = SessionMemory(
                tenant_id=tenant_id,
                mode=mode,
                project_id=project_id,
                user_id=user_id,
                session_id=session_id,
            )
        session.messages.append(message)
        self._store.save_session(session)
        return session.dict()
    
    def get_session(self, tenant_id: str, mode: str, project_id: str, user_id: str, session_id: str):
        session = self._store.get_session(tenant_id, mode, project_id, user_id, session_id)
        return session.dict() if session else None
    
    def write_blackboard(self, board: Blackboard) -> Blackboard:
        self._store.save_blackboard(board)
        return board
    
    def get_blackboard(self, tenant_id: str, mode: str, project_id: str, key: str):
        board = self._store.get_blackboard(tenant_id, mode, project_id, key)
        return board.dict() if board else None
    
    def delete_blackboard(self, tenant_id: str, mode: str, project_id: str, key: str) -> None:
        self._store.delete_blackboard(tenant_id, mode, project_id, key)

_default_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _default_service
    if _default_service is None:
        _default_service = MemoryService()
    return _default_service


def set_memory_service(service: MemoryService) -> None:
    global _default_service
    _default_service = service
