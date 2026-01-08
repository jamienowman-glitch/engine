from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.common.error_envelope import error_response
from engines.firearms.models import Firearm, FirearmGrant, FirearmBinding, FirearmDecision
from engines.firearms.repository import FirearmsRepository, get_firearms_repo
from engines.logging.audit import emit_audit_event

# Data-driven policy: no static bindings. Empty list kept for backward imports only.
DANGEROUS_ACTIONS: list[str] = []


class FirearmsService:
    def __init__(self, repo: Optional[FirearmsRepository] = None) -> None:
        self.repo = repo or get_firearms_repo()

    def check_access(self, ctx: RequestContext, action: str) -> FirearmDecision:
        """
        Check if action requires a firearm and if the actor has it.
        Returns FirearmDecision.
        """
        # 1. Check Binding
        binding = self.repo.get_binding(ctx, action)
        if not binding:
            return FirearmDecision(allowed=True, reason="no_binding")
            
        # 2. Check Grant
        # We need to find a valid grant for this firearm for this actor (agent or user) in this tenant
        
        # Hack/Improvement: RequestContext doesn't formally have actor_type in some versions?
        # Let's assume defaults.
        actor_type = getattr(ctx, "actor_type", None) or (
            "agent" if getattr(ctx, "actor_id", None) else ("user" if ctx.user_id else "unknown")
        )
        
        grants = self.repo.list_grants(
            ctx=ctx,
            agent_id=ctx.actor_id if actor_type == "agent" else None,
            user_id=ctx.user_id if actor_type != "agent" else None,
        )
        
        # Filter for specific firearm
        valid_grant = next(
            (g for g in grants 
             if g.firearm_id == binding.firearm_id 
             and (not g.expires_at or g.expires_at > datetime.now(timezone.utc))),
            None
        )
        
        if not valid_grant:
            return FirearmDecision(
                allowed=False, 
                reason="firearms.license_required",
                firearm_id=binding.firearm_id,
                required_license_types=[binding.firearm_id]
            )
            
        # 3. Allowed, but requires Strategy Lock
        return FirearmDecision(
            allowed=True,
            reason="grant_valid",
            firearm_id=binding.firearm_id,
            required_license_types=[binding.firearm_id],
            strategy_lock_required=binding.strategy_lock_required
        )

    def require_licence_or_raise(self, ctx: RequestContext, subject_type: str, subject_id: str, action: str) -> None:
        """
        Legacy/Compat method name, updated to use new logic.
        Passes subject info but main check is on 'action' vs 'binding'.
        """
        decision = self.check_access(ctx, action)
        if not decision.allowed:
            error_response(
                code="firearms.license_required",
                message="Firearm license required for this action",
                status_code=403,
                gate="firearms",
                action_name=action,
                details={
                    "firearm_id": decision.firearm_id,
                    "action": action,
                    "required_license_types": decision.required_license_types,
                },
            )

    # CRUD Wrappers
    def register_firearm(self, ctx: RequestContext, firearm: Firearm) -> Firearm:
        return self.repo.create_firearm(ctx, firearm)

    def list_firearms(self, ctx: RequestContext) -> List[Firearm]:
        return self.repo.list_firearms(ctx)

    def bind_action(self, ctx: RequestContext, binding: FirearmBinding) -> FirearmBinding:
        return self.repo.create_binding(ctx, binding)

    def grant_licence(self, ctx: RequestContext, grant: FirearmGrant) -> FirearmGrant:
        grant.granted_by = ctx.user_id or "system"
        grant.tenant_id = ctx.tenant_id # Ensure tenant scope match context
        saved = self.repo.create_grant(ctx, grant)
        emit_audit_event(ctx, action="firearms.grant", surface="firearms", metadata={"grant_id": saved.id, "firearm_id": saved.firearm_id})
        return saved

    def list_grants(self, ctx: RequestContext, agent_id: Optional[str] = None, user_id: Optional[str] = None) -> List[FirearmGrant]:
        return self.repo.list_grants(ctx, agent_id=agent_id, user_id=user_id or ctx.user_id)

    def list_licences(self, ctx: RequestContext, status: Optional[str] = None, agent_id: Optional[str] = None, user_id: Optional[str] = None) -> List[FirearmGrant]:
        """Legacy alias for list_grants to preserve callers."""
        return self.list_grants(ctx, agent_id=agent_id, user_id=user_id)


_default_service: Optional[FirearmsService] = None

def get_firearms_service() -> FirearmsService:
    global _default_service
    if _default_service is None:
        _default_service = FirearmsService()
    return _default_service

def set_firearms_service(service: FirearmsService) -> None:
    global _default_service
    _default_service = service
