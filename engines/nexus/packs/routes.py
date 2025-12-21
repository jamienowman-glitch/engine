"""Influence Pack API Routes (PHASE_02 enforces tenant-scoped auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.index.models import SearchQuery
from engines.nexus.packs.models import InfluencePack
from engines.nexus.packs.service import PackService
from pydantic import BaseModel

from typing import Any, Dict, Optional

router = APIRouter(prefix="/nexus/influence-pack", tags=["nexus_packs"])


class CreatePackRequest(BaseModel):
    query: SearchQuery
    filters: Optional[Dict[str, Any]] = None


def get_service() -> PackService:
    return PackService()


from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

@router.post("", response_model=InfluencePack)
def create_pack(
    request: CreatePackRequest = Body(...),
    service: PackService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> InfluencePack:
    """Create an Influence Pack from a search query."""
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "pack_create")
    limiter.check_rate_limit(ctx, "pack_create")
    return service.create_pack(ctx, request.query)
