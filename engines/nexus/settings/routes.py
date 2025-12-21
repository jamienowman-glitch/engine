"""Settings API Routes (Phase 02 requires auth/context)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.cards.models import Card
from engines.nexus.settings.service import SettingsService
from engines.nexus.settings.models import SettingsResponse

router = APIRouter(prefix="/nexus/settings", tags=["nexus_settings"])


def get_service() -> SettingsService:
    return SettingsService()


from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

@router.get("/surface", response_model=SettingsResponse)
def get_surface_settings(
    service: SettingsService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> SettingsResponse:
    """Get the active surface settings card."""
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "settings_read")
    limiter.check_rate_limit(ctx, "settings_read")
    return service.get_surface_settings(ctx)


@router.get("/apps", response_model=SettingsResponse)
def get_apps(
    service: SettingsService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> SettingsResponse:
    """Get installed app definition cards."""
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "settings_read")
    limiter.check_rate_limit(ctx, "settings_read")
    return service.get_apps(ctx)


@router.get("/connectors", response_model=SettingsResponse)
def get_connectors(
    service: SettingsService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    kill_switch: KillSwitchService = Depends(get_kill_switch_service),
    limiter: RateLimitService = Depends(get_rate_limiter),
) -> SettingsResponse:
    """Get configured connector cards."""
    enforce_tenant_context(ctx, auth)
    kill_switch.ensure_action_allowed(ctx, "settings_read")
    limiter.check_rate_limit(ctx, "settings_read")
    return service.get_connectors(ctx)
