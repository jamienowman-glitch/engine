"""Analytics config resolver helper (SELECTA-style)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from engines.common.identity import RequestContext
from engines.identity.analytics_service import AnalyticsConfigService, get_analytics_service, set_analytics_service
from engines.identity.models import TenantAnalyticsConfig


@dataclass
class EffectiveAnalyticsConfig:
    tenant_id: str
    env: str
    surface: str
    ga4_measurement_id: Optional[str]
    ga4_api_secret_slot: Optional[str]
    meta_pixel_id: Optional[str]
    tiktok_pixel_id: Optional[str]
    snap_pixel_id: Optional[str]
    extra: dict
    source: Literal["tenant", "system"]


class AnalyticsResolver:
    """Resolve effective analytics config with tenant → system fallback."""

    def __init__(self, service: Optional[AnalyticsConfigService] = None, system_tenant: str = "system") -> None:
        self.service = service or get_analytics_service()
        self.system_tenant = system_tenant

    def resolve(self, ctx: RequestContext, surface: str) -> Optional[EffectiveAnalyticsConfig]:
        cfg = self.service.resolve_effective(ctx.tenant_id, ctx.env, surface, system_tenant=self.system_tenant)
        if not cfg:
            return None
        return _to_effective(cfg, ctx.tenant_id)


def _to_effective(cfg: TenantAnalyticsConfig, requested_tenant: str) -> EffectiveAnalyticsConfig:
    source: Literal["tenant", "system"] = "tenant" if cfg.tenant_id == requested_tenant else "system"
    return EffectiveAnalyticsConfig(
        tenant_id=cfg.tenant_id,
        env=cfg.env,
        surface=cfg.surface,
        ga4_measurement_id=cfg.ga4_measurement_id,
        ga4_api_secret_slot=cfg.ga4_api_secret_slot,
        meta_pixel_id=cfg.meta_pixel_id,
        tiktok_pixel_id=cfg.tiktok_pixel_id,
        snap_pixel_id=cfg.snap_pixel_id,
        extra=cfg.extra or {},
        source=source,
    )


_default_resolver: Optional[AnalyticsResolver] = None


def get_analytics_resolver() -> AnalyticsResolver:
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = AnalyticsResolver()
    return _default_resolver


def set_analytics_resolver(resolver: AnalyticsResolver) -> None:
    global _default_resolver
    _default_resolver = resolver
    # Keep the shared service pointer in sync for callers that pull directly.
    set_analytics_service(resolver.service)
