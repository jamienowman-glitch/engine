"""Atom API Routes (PHASE_02 enforces RequestContext + AuthContext)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Body, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.nexus.atoms.models import AtomArtifact
from engines.nexus.atoms.service import AtomService
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

router = APIRouter(prefix="/nexus/atoms", tags=["nexus_atoms"])


def get_service() -> AtomService:
    # In a real app with DI, we'd inject the repo here.
    return AtomService()


@router.post("/create-from-raw", response_model=AtomArtifact)
def create_atom_from_raw(
    raw_asset_id: str,
    op_type: str,
    service: AtomService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> AtomArtifact:
    """Turn a RawAsset into an AtomArtifact (idempotent)."""
    enforce_tenant_context(ctx, auth)
    
    try:
        # GateChain + KillSwitch + RateLimit
        gate_chain.run(ctx, action="atom_create", surface="atoms", subject_type="atom")
        kill_switch.ensure_action_allowed(ctx, "atom_create")
        limiter.check_rate_limit(ctx, "atom_create")
        
        return service.create_atom_from_raw(ctx, raw_asset_id, op_type)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.atom_create_failed", message=str(exc), status_code=500)


@router.get("/{atom_id}", response_model=AtomArtifact)
def get_atom(
    atom_id: str,
    service: AtomService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> AtomArtifact:
    """Retrieve an atom by ID."""
    enforce_tenant_context(ctx, auth)
    
    try:
        kill_switch.ensure_action_allowed(ctx, "atom_read")
        limiter.check_rate_limit(ctx, "atom_read")
        return service.get_atom(ctx, atom_id)
    except HTTPException:
        raise
    except Exception as exc:
        if "not found" in str(exc).lower():
            return error_response(code="nexus.atom_not_found", message=str(exc), status_code=404)
        return error_response(code="nexus.atom_read_failed", message=str(exc), status_code=500)
