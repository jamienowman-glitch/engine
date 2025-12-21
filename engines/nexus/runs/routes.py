"""Research Run API Routes (Phase 02 requires auth/context)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.runs.models import ResearchRun
from engines.nexus.runs.service import ResearchRunService

router = APIRouter(prefix="/nexus/runs", tags=["nexus_runs"])


def get_service() -> ResearchRunService:
    return ResearchRunService()


from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

@router.get("", response_model=List[ResearchRun])
def list_runs(
    limit: int = Query(50, le=100),
    service: ResearchRunService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> List[ResearchRun]:
    """Get research runs (activity history) for the tenant."""
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "runs_read")
    limiter.check_rate_limit(ctx, "runs_read")
    return service.list_runs(ctx, limit=limit)
