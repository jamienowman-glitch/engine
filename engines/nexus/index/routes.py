"""Index/Search API Routes (PHASE_02: tenant-scoped auth guard)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Body, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.nexus.index.models import SearchQuery, SearchResult
from engines.nexus.index.service import CardIndexService
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

router = APIRouter(prefix="/nexus/search", tags=["nexus_search"])


def get_service() -> CardIndexService:
    return CardIndexService()


@router.post("", response_model=List[SearchResult])
def search(
    query: SearchQuery,
    service: CardIndexService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> List[SearchResult]:
    """
    Search for cards using vector similarity + metadata filters.
    """
    enforce_tenant_context(ctx, auth)
    
    try:
        # GateChain + KillSwitch + RateLimit
        gate_chain.run(ctx, action="search", surface="index", subject_type="query")
        kill_switch.ensure_action_allowed(ctx, "search")
        limiter.check_rate_limit(ctx, "search")
        
        return service.search(ctx, query)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.search_failed", message=str(exc), status_code=500)
