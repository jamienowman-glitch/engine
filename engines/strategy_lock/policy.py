from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Protocol

from pydantic import BaseModel, Field

from engines.common.error_envelope import missing_route_error
from engines.common.identity import RequestContext
from engines.storage.routing_service import TabularStoreService
from engines.strategy_lock.config_repository import get_strategy_lock_config_repo


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StrategyPolicyBinding(BaseModel):
    """Binding that declares whether an action requires a strategy lock."""

    action_name: str
    requires_strategy_lock: bool = True
    surface_id: Optional[str] = None
    project_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    tenant_id: Optional[str] = None
    env: Optional[str] = None
    mode: Optional[str] = None


class StrategyPolicyRepository(Protocol):
    def list_bindings(self, ctx: RequestContext) -> List[StrategyPolicyBinding]:
        ...

    def save_binding(self, ctx: RequestContext, binding: StrategyPolicyBinding) -> StrategyPolicyBinding:
        ...

    def get_binding(
        self,
        ctx: RequestContext,
        action_name: str,
        surface_id: Optional[str] = None,
    ) -> Optional[StrategyPolicyBinding]:
        ...


class RoutedStrategyPolicyRepository(StrategyPolicyRepository):
    """Routed persistence via strategy_policy_store."""

    TABLE_NAME = "strategy_policy_bindings"

    def _tabular(self, ctx: RequestContext) -> TabularStoreService:
        try:
            return TabularStoreService(ctx, resource_kind="strategy_policy_store")
        except RuntimeError as exc:
            raise missing_route_error(
                resource_kind="strategy_policy_store",
                tenant_id=ctx.tenant_id,
                env=ctx.env,
            ) from exc

    def _binding_key(self, ctx: RequestContext, action_name: str, surface_id: Optional[str]) -> str:
        surface_seg = surface_id or "global"
        project_seg = ctx.project_id or "project"
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#binding#{action_name}#{surface_seg}#{project_seg}"

    def _prefix(self, ctx: RequestContext) -> str:
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#binding#"

    def list_bindings(self, ctx: RequestContext) -> List[StrategyPolicyBinding]:
        records = self._tabular(ctx).list_by_prefix(self.TABLE_NAME, self._prefix(ctx))
        return [StrategyPolicyBinding(**record) for record in records if record]

    def save_binding(self, ctx: RequestContext, binding: StrategyPolicyBinding) -> StrategyPolicyBinding:
        binding.tenant_id = ctx.tenant_id
        binding.env = ctx.env
        binding.mode = ctx.mode
        binding.project_id = binding.project_id or ctx.project_id
        binding.surface_id = binding.surface_id or ctx.surface_id
        record = binding.model_dump()
        self._tabular(ctx).upsert(
            self.TABLE_NAME,
            self._binding_key(ctx, binding.action_name, binding.surface_id),
            record,
        )
        return binding

    def get_binding(
        self,
        ctx: RequestContext,
        action_name: str,
        surface_id: Optional[str] = None,
    ) -> Optional[StrategyPolicyBinding]:
        for target_surface in (surface_id, ctx.surface_id, "global"):
            key = self._binding_key(ctx, action_name, target_surface)
            data = self._tabular(ctx).get(self.TABLE_NAME, key)
            if data:
                return StrategyPolicyBinding(**data)
        return None


class StrategyPolicyService:
    def __init__(self, repo: Optional[StrategyPolicyRepository] = None) -> None:
        self.repo = repo or RoutedStrategyPolicyRepository()

    def list_policies(self, ctx: RequestContext) -> List[StrategyPolicyBinding]:
        return self.repo.list_bindings(ctx)

    def save_policies(self, ctx: RequestContext, bindings: List[StrategyPolicyBinding]) -> List[StrategyPolicyBinding]:
        saved: list[StrategyPolicyBinding] = []
        for binding in bindings:
            saved.append(self.repo.save_binding(ctx, binding))
        return saved

    def requires_strategy_lock(
        self,
        ctx: RequestContext,
        action_name: str,
        surface_id: Optional[str],
    ) -> bool:
        if not action_name:
            return False
        config = get_strategy_lock_config_repo().get(ctx)
        if config.defaults.get("enabled") is False:
            return False
        binding = self.repo.get_binding(ctx, action_name, surface_id=surface_id)
        if binding:
            return binding.requires_strategy_lock
        if action_name.startswith("tool"):
            return config.defaults.get("require_for_tools", False)
        if action_name.startswith("canvas"):
            return config.defaults.get("require_for_canvas", False)
        return False


_policy_service: Optional[StrategyPolicyService] = None


def get_strategy_policy_service() -> StrategyPolicyService:
    global _policy_service
    if _policy_service is None:
        _policy_service = StrategyPolicyService()
    return _policy_service


def set_strategy_policy_service(service: StrategyPolicyService) -> None:
    global _policy_service
    _policy_service = service
