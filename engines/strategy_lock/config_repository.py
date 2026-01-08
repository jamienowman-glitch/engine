from __future__ import annotations

from typing import Optional, Protocol, Dict, Any
from pydantic import BaseModel

from engines.common.identity import RequestContext
from engines.storage.versioned_store import ScopeConfig, VersionedStore


class StrategyLockConfig(BaseModel):
    """Configuration for Strategy Lock requirements."""
    defaults: Dict[str, bool] = {} # e.g. {"require_for_tools": False}
    overrides: Dict[str, Dict[str, bool]] = {} # e.g. {"nodes": {"node_1": True}}


class StrategyLockConfigRepository(Protocol):
    def get(self, context: RequestContext) -> StrategyLockConfig: ...
    def update(self, context: RequestContext, config: StrategyLockConfig) -> StrategyLockConfig: ...


class InMemoryStrategyLockConfigRepository:
    def __init__(self) -> None:
        self._configs: Dict[str, StrategyLockConfig] = {}

    def _key(self, ctx: RequestContext) -> str:
        return f"{ctx.tenant_id}:{ctx.env}"

    def get(self, context: RequestContext) -> StrategyLockConfig:
        return self._configs.get(self._key(context), StrategyLockConfig())

    def update(self, context: RequestContext, config: StrategyLockConfig) -> StrategyLockConfig:
        self._configs[self._key(context)] = config
        return config


class RoutedStrategyLockConfigRepository:
    """Versioned, routed persistence via strategy_lock_config store."""

    def __init__(self) -> None:
        # Config is typically system/tenant scoped, but we might want surface overrides?
        # For now, let's stick to Tenant/Env scope primarily, maybe Surface.
        self._scope_cfg = ScopeConfig(include_surface=False, include_app=False, include_user=False)

    def _store(self, context: RequestContext) -> VersionedStore:
        return VersionedStore(
            context,
            resource_kind="strategy_lock_config",
            table_name="strategy_lock_config",
            scope_config=self._scope_cfg,
        )

    def get(self, context: RequestContext) -> StrategyLockConfig:
        store = self._store(context)
        # We use a singleton ID "config" per tenant/env scope
        record = store.get_latest("config", user_id="system", surface_id="system")
        if record and not record.get("deleted"):
            return StrategyLockConfig(**record)
        return StrategyLockConfig()

    def update(self, context: RequestContext, config: StrategyLockConfig) -> StrategyLockConfig:
        store = self._store(context)
        payload = config.model_dump(mode="json")
        payload["mode"] = context.mode
        saved = store.save_new("config", payload, user_id=context.user_id or "system", surface_id="system")
        return StrategyLockConfig(**saved)

_config_repo: Optional[StrategyLockConfigRepository] = None

def get_strategy_lock_config_repo() -> StrategyLockConfigRepository:
    global _config_repo
    if _config_repo is None:
        _config_repo = InMemoryStrategyLockConfigRepository()
    return _config_repo

def set_strategy_lock_config_repo(repo: StrategyLockConfigRepository) -> None:
    global _config_repo
    _config_repo = repo
