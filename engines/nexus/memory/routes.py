"""Session Memory API Routes (Phase 02 enforces tenant auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.nexus.memory.models import SessionSnapshot, SessionTurn
from engines.nexus.memory.service import SessionMemoryService

router = APIRouter(prefix="/nexus/memory", tags=["nexus_memory"])


def get_service() -> SessionMemoryService:
    return SessionMemoryService()


from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

@router.post("/session/{session_id}/turn", response_model=SessionTurn)
def add_turn(
    turn: SessionTurn,
    session_id: str = Path(..., description="Session ID"),
    service: SessionMemoryService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> SessionTurn:
    """Append a turn to the session."""
    enforce_tenant_context(ctx, auth)
    gate_chain.run(
        ctx,
        action="memory_write",
        surface="memory",
        subject_type="session",
        subject_id=session_id,
    )
    limiter.check_rate_limit(ctx, "memory_write")
    return service.add_turn(ctx, session_id, turn)


@router.get("/session/{session_id}", response_model=SessionSnapshot)
def get_session(
    session_id: str = Path(..., description="Session ID"),
    service: SessionMemoryService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> SessionSnapshot:
    """Get full session history."""
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "memory_read")
    limiter.check_rate_limit(ctx, "memory_read")
    return service.get_session(ctx, session_id)
