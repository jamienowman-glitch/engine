from __future__ import annotations

from typing import List, Optional, Protocol, Dict

from engines.common.identity import RequestContext
from engines.common.error_envelope import missing_route_error
from engines.storage.routing_service import TabularStoreService
from engines.routing.registry import MissingRoutingConfig
from engines.firearms.models import Firearm, FirearmGrant, FirearmBinding


class FirearmsRepository(Protocol):
    # Registry
    def create_firearm(self, ctx: RequestContext, firearm: Firearm) -> Firearm: ...
    def get_firearm(self, ctx: RequestContext, firearm_id: str) -> Optional[Firearm]: ...
    def list_firearms(self, ctx: RequestContext) -> List[Firearm]: ...
    
    # Grants
    def create_grant(self, ctx: RequestContext, grant: FirearmGrant) -> FirearmGrant: ...
    def list_grants(self, ctx: RequestContext, agent_id: Optional[str] = None, user_id: Optional[str] = None) -> List[FirearmGrant]: ...
    
    # Bindings
    def create_binding(self, ctx: RequestContext, binding: FirearmBinding) -> FirearmBinding: ...
    def get_binding(self, ctx: RequestContext, action_name: str) -> Optional[FirearmBinding]: ...
    def list_bindings(self, ctx: RequestContext) -> List[FirearmBinding]: ...


class InMemoryFirearmsRepository:
    def __init__(self) -> None:
        self._firearms: Dict[str, Firearm] = {}
        self._grants: Dict[str, FirearmGrant] = {}
        self._bindings: Dict[str, FirearmBinding] = {}

    def create_firearm(self, ctx: RequestContext, firearm: Firearm) -> Firearm:
        key = f"{ctx.tenant_id}:{firearm.id}"
        self._firearms[key] = firearm
        return firearm

    def get_firearm(self, ctx: RequestContext, firearm_id: str) -> Optional[Firearm]:
        key = f"{ctx.tenant_id}:{firearm_id}"
        return self._firearms.get(key)

    def list_firearms(self, ctx: RequestContext) -> List[Firearm]:
        prefix = f"{ctx.tenant_id}:"
        return [f for k, f in self._firearms.items() if k.startswith(prefix)]

    def create_grant(self, ctx: RequestContext, grant: FirearmGrant) -> FirearmGrant:
        self._grants[grant.id] = grant
        return grant

    def list_grants(self, ctx: RequestContext, agent_id: Optional[str] = None, user_id: Optional[str] = None) -> List[FirearmGrant]:
        res = [
            g for g in self._grants.values() 
            if g.tenant_id == ctx.tenant_id
            and (not g.revoked)
        ]
        if agent_id:
            res = [g for g in res if g.granted_to_agent_id == agent_id]
        if user_id:
            res = [g for g in res if g.granted_to_user_id == user_id]
        return res

    def create_binding(self, ctx: RequestContext, binding: FirearmBinding) -> FirearmBinding:
        self._bindings[binding.action_name] = binding
        return binding

    def get_binding(self, ctx: RequestContext, action_name: str) -> Optional[FirearmBinding]:
        return self._bindings.get(action_name)
    
    def list_bindings(self, ctx: RequestContext) -> List[FirearmBinding]:
        return list(self._bindings.values())


class RoutedFirearmsRepository(InMemoryFirearmsRepository):
    """Routed firearms policy store (firearms_policy_store)."""

    def __init__(self) -> None:
        super().__init__()
        self._bindings_table = "firearms_policy"
        self._grants_table = "firearms_grants"

    def _tabular(self, ctx: RequestContext) -> TabularStoreService:
        try:
            return TabularStoreService(ctx, resource_kind="firearms_policy_store")
        except (RuntimeError, MissingRoutingConfig):
            missing_route_error(
                resource_kind="firearms_policy_store",
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                status_code=503,
            )

    def _binding_key(self, ctx: RequestContext, action_name: str) -> str:
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#binding#{action_name}"

    def _grant_prefix(self, ctx: RequestContext) -> str:
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#grant#"

    def _grant_key(self, ctx: RequestContext, grant: FirearmGrant) -> str:
        actor = grant.granted_to_agent_id or grant.granted_to_user_id or "unknown"
        return f"{self._grant_prefix(ctx)}{actor}#{grant.firearm_id}#{grant.id}"

    def create_binding(self, ctx: RequestContext, binding: FirearmBinding) -> FirearmBinding:
        record = binding.model_dump()
        self._tabular(ctx).upsert(self._bindings_table, self._binding_key(ctx, binding.action_name), record)
        return binding

    def get_binding(self, ctx: RequestContext, action_name: str) -> Optional[FirearmBinding]:
        data = self._tabular(ctx).get(self._bindings_table, self._binding_key(ctx, action_name))
        return FirearmBinding(**data) if data else None

    def list_bindings(self, ctx: RequestContext) -> List[FirearmBinding]:
        records = self._tabular(ctx).list_by_prefix(self._bindings_table, f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#binding#")
        return [FirearmBinding(**r) for r in records if r]

    def create_grant(self, ctx: RequestContext, grant: FirearmGrant) -> FirearmGrant:
        record = grant.model_dump()
        self._tabular(ctx).upsert(self._grants_table, self._grant_key(ctx, grant), record)
        return grant

    def list_grants(self, ctx: RequestContext, agent_id: Optional[str] = None, user_id: Optional[str] = None) -> List[FirearmGrant]:
        prefix = self._grant_prefix(ctx)
        records = self._tabular(ctx).list_by_prefix(self._grants_table, prefix)
        result = []
        for rec in records:
            try:
                g = FirearmGrant(**rec)
            except Exception:
                continue
            if g.revoked or g.tenant_id != ctx.tenant_id:
                continue
            if agent_id and g.granted_to_agent_id != agent_id:
                continue
            if user_id and g.granted_to_user_id != user_id:
                continue
            result.append(g)
        return result

    def create_firearm(self, ctx: RequestContext, firearm: Firearm) -> Firearm:
        record = firearm.model_dump()
        key = f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#firearm#{firearm.id}"
        self._tabular(ctx).upsert(self._bindings_table, key, record)
        return firearm

    def get_firearm(self, ctx: RequestContext, firearm_id: str) -> Optional[Firearm]:
        key_prefix = f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#firearm#{firearm_id}"
        records = self._tabular(ctx).list_by_prefix(self._bindings_table, key_prefix)
        rec = records[0] if records else None
        return Firearm(**rec) if rec else None

    def list_firearms(self, ctx: RequestContext) -> List[Firearm]:
        key_prefix = f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#firearm#"
        records = self._tabular(ctx).list_by_prefix(self._bindings_table, key_prefix)
        return [Firearm(**r) for r in records if r]


# Global singleton
_firearms_repo: FirearmsRepository = RoutedFirearmsRepository()

def get_firearms_repo() -> FirearmsRepository:
    return _firearms_repo

def set_firearms_repo(repo: FirearmsRepository) -> None:
    global _firearms_repo
    _firearms_repo = repo
