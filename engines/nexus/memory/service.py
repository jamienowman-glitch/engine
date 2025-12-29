"""Session Memory Service with durable backend requirement."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.memory.models import MessageRecord
from engines.memory.repository import MemoryRepository, memory_repo_from_env
from engines.nexus.memory.models import SessionSnapshot, SessionTurn


def _require_memory_scope(ctx: RequestContext) -> tuple[str, str]:
    if not ctx.user_id:
        raise RuntimeError("user_id required for session memory persistence")
    if not ctx.mode:
        raise RuntimeError("mode required for session memory persistence")
    if not ctx.project_id:
        raise RuntimeError("project_id required for session memory persistence")
    return ctx.mode, ctx.project_id


class SessionMemoryService:
    def __init__(self, repo: Optional[MemoryRepository] = None) -> None:
        self._repo = repo or memory_repo_from_env()

    def add_turn(self, ctx: RequestContext, session_id: str, turn: SessionTurn) -> SessionTurn:
        """
        Append a turn to the session.
        Enforces tenancy via storage key.
        """
        mode, project_id = _require_memory_scope(ctx)

        # Ensure turn session_id matches
        if turn.session_id != session_id:
            turn.session_id = session_id

        metadata = dict(turn.metadata)
        metadata.setdefault("turn_id", turn.turn_id)

        message = MessageRecord(
            role=turn.role,
            content=turn.content,
            timestamp=turn.timestamp,
            metadata=metadata,
        )
        self._repo.append_message(
            ctx.tenant_id, mode, project_id, ctx.user_id, session_id, message
        )
        
        # Log event
        default_event_logger(
            EventLogEntry(
                event_type="memory_turn_created",
                asset_type="session_turn",
                asset_id=turn.turn_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={
                    "session_id": session_id,
                    "mode": mode,
                    "project_id": project_id,
                    "role": turn.role,
                    "content_len": len(turn.content)
                }
            )
        )
        return turn

    def get_session(self, ctx: RequestContext, session_id: str) -> SessionSnapshot:
        """
        Retrieve session snapshot.
        """
        mode, project_id = _require_memory_scope(ctx)
        session = self._repo.get_session(
            ctx.tenant_id, mode, project_id, ctx.user_id, session_id
        )
        turns: List[SessionTurn] = []
        if session:
            for msg in session.messages:
                turn_kwargs = {
                    "session_id": session_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata,
                }
                stored_turn_id = msg.metadata.get("turn_id") if msg.metadata else None
                if stored_turn_id:
                    turn_kwargs["turn_id"] = stored_turn_id
                turns.append(SessionTurn(**turn_kwargs))

        # Log read
        default_event_logger(
            EventLogEntry(
                event_type="memory_session_read",
                asset_type="session",
                asset_id=session_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={
                    "turn_count": len(turns),
                    "mode": mode,
                    "project_id": project_id,
                }
            )
        )

        created_at = session.created_at if session else datetime.now(timezone.utc)
        updated_at = session.updated_at if session else created_at
        return SessionSnapshot(
            session_id=session_id,
            tenant_id=ctx.tenant_id,
            mode=mode,
            project_id=project_id,
            turns=turns,
            created_at=created_at,
            updated_at=updated_at,
        )
