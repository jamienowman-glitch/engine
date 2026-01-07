"""Influence Pack API Routes (PHASE_02 enforces tenant-scoped auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.nexus.index.models import SearchQuery
from engines.nexus.packs.models import InfluencePack
from engines.nexus.packs.service import PackService
from pydantic import BaseModel

from typing import Any, Dict, Optional
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

router = APIRouter(prefix="/nexus/influence-pack", tags=["nexus_packs"])


class CreatePackRequest(BaseModel):
    query: SearchQuery
    filters: Optional[Dict[str, Any]] = None


def get_service() -> PackService:
    return PackService()


@router.post("", response_model=InfluencePack)
def create_pack(
    request: CreatePackRequest = Body(...),
    service: PackService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> InfluencePack:
    """Create an Influence Pack from a search query."""
    enforce_tenant_context(ctx, auth)
    
    try:
        # GateChain + KillSwitch + RateLimit
        gate_chain.run(ctx, action="pack_create", surface="packs", subject_type="influence_pack")
        kill_switch.ensure_action_allowed(ctx, "pack_create")
        limiter.check_rate_limit(ctx, "pack_create")
        
        return service.create_pack(ctx, request.query)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.pack_create_failed", message=str(exc), status_code=500)
