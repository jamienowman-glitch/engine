"""Index/Search API Routes (PHASE_02: tenant-scoped auth guard)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Body

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.index.models import SearchQuery, SearchResult
from engines.nexus.index.service import CardIndexService

router = APIRouter(prefix="/nexus/search", tags=["nexus_search"])


def get_service() -> CardIndexService:
    return CardIndexService()


from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

@router.post("", response_model=List[SearchResult])
def search(
    query: SearchQuery,
    service: CardIndexService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> List[SearchResult]:
    """
    Search for cards using vector similarity + metadata filters.
    """
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "search")
    limiter.check_rate_limit(ctx, "search")
    return service.search(ctx, query)
