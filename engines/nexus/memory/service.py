"""Session Memory Service (Placeholder)."""
from __future__ import annotations

from typing import Dict, List, Optional
from collections import defaultdict

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.memory.models import SessionSnapshot, SessionTurn

# In-Memory Storage for Phase 8
# Key: (tenant_id, env, session_id) -> List[SessionTurn]
_GLOBAL_MEMORY: Dict[tuple, List[SessionTurn]] = defaultdict(list)


class SessionMemoryService:
    def add_turn(self, ctx: RequestContext, session_id: str, turn: SessionTurn) -> SessionTurn:
        """
        Append a turn to the session.
        Enforces tenancy via storage key.
        """
        key = (ctx.tenant_id, ctx.env, session_id)
        
        # Ensure turn session_id matches
        if turn.session_id != session_id:
             # Force match or error? Overwriting for consistency
             turn.session_id = session_id
             
        _GLOBAL_MEMORY[key].append(turn)
        
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
        key = (ctx.tenant_id, ctx.env, session_id)
        turns = _GLOBAL_MEMORY.get(key, [])
        
        # Log read
        default_event_logger(
            EventLogEntry(
                event_type="memory_session_read",
                asset_type="session",
                asset_id=session_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={"turn_count": len(turns)}
            )
        )
        
        return SessionSnapshot(
            session_id=session_id,
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            turns=turns
        )
