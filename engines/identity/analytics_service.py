from __future__ import annotations

from typing import List, Optional

from engines.identity.models import TenantAnalyticsConfig
from engines.identity.repository import IdentityRepository
from engines.identity.state import identity_repo


class AnalyticsConfigService:
    def __init__(self, repo: Optional[IdentityRepository] = None) -> None:
        self._repo = repo or identity_repo

    def upsert_config(self, config: TenantAnalyticsConfig) -> TenantAnalyticsConfig:
        return self._repo.upsert_analytics_config(config)

    def list_configs(self, tenant_id: str, env: Optional[str] = None, surface: Optional[str] = None) -> List[TenantAnalyticsConfig]:
        return self._repo.list_analytics_configs(tenant_id, env, surface)

    def get_config(self, tenant_id: str, env: str, surface: str) -> Optional[TenantAnalyticsConfig]:
        return self._repo.get_analytics_config(tenant_id, env, surface)

    def resolve_effective(self, tenant_id: str, env: str, surface: str, system_tenant: str = "system") -> Optional[TenantAnalyticsConfig]:
        candidates = [
            (tenant_id, env),
            (tenant_id, "prod"),
            (system_tenant, env),
            (system_tenant, "prod"),
        ]
        for t, e in candidates:
            cfg = self.get_config(t, e, surface)
            if cfg:
                return cfg
        return None


_default_service: Optional[AnalyticsConfigService] = None


def get_analytics_service() -> AnalyticsConfigService:
    global _default_service
    if _default_service is None:
        _default_service = AnalyticsConfigService()
    return _default_service


def set_analytics_service(svc: AnalyticsConfigService) -> None:
    global _default_service
    _default_service = svc
