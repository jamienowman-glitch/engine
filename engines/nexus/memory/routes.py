"""Session Memory API Routes (Phase 02 enforces tenant auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, HTTPException

from engines.common.error_envelope import error_response

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

from engines.common.error_envelope import error_response

# ... (imports)

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
    
    try:
        gate_chain.run(
            ctx,
            action="memory_write",
            surface="memory",
            subject_type="session",
            subject_id=session_id,
        )
        limiter.check_rate_limit(ctx, "memory_write")
        return service.add_turn(ctx, session_id, turn)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.memory_write_failed", message=str(exc), status_code=500)


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
    
    try:
        kill_switch.ensure_action_allowed(ctx, "memory_read")
        limiter.check_rate_limit(ctx, "memory_read")
        return service.get_session(ctx, session_id)
    except HTTPException:
        raise
    except Exception as exc:
        if "not found" in str(exc).lower():
            return error_response(code="nexus.session_not_found", message=str(exc), status_code=404)
        return error_response(code="nexus.memory_read_failed", message=str(exc), status_code=500)
