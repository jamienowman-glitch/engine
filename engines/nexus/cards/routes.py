"""Card API Routes (PHASE_02: strict RequestContext + AuthContext enforcement)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Body, HTTPException

from engines.common.error_envelope import error_response

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.nexus.cards.models import Card
from engines.nexus.cards.service import CardService

router = APIRouter(prefix="/nexus/cards", tags=["nexus_cards"])


def get_service() -> CardService:
    return CardService()


from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

from engines.common.error_envelope import error_response

# ... (imports)

@router.post("", response_model=Card)
def create_card(
    card_text: str = Body(..., media_type="text/plain"),
    service: CardService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> Card:
    """Create a new card from raw YAML+NL text."""
    enforce_tenant_context(ctx, auth)
    
    try:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
        limiter.check_rate_limit(ctx, "card_create")
        return service.create_card(ctx, card_text)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.card_create_failed", message=str(exc), status_code=500)


@router.get("/{card_id}", response_model=Card)
def get_card(
    card_id: str,
    service: CardService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> Card:
    """Retrieve a card by ID."""
    enforce_tenant_context(ctx, auth)
    
    try:
        kill_switch.ensure_action_allowed(ctx, "card_read")
        limiter.check_rate_limit(ctx, "card_read")
        return service.get_card(ctx, card_id)
    except HTTPException:
        raise
    except Exception as exc:
        # Check for not found in message if not strict exception
        if "not found" in str(exc).lower():
            return error_response(code="nexus.card_not_found", message=str(exc), status_code=404)
        return error_response(code="nexus.card_read_failed", message=str(exc), status_code=500)
