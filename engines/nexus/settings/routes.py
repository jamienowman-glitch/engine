"""Settings API Routes (Phase 02 requires auth/context)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.settings.service import SettingsService
from engines.nexus.settings.models import SettingsResponse
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.nexus.hardening.rate_limit import RateLimitService, get_rate_limiter

router = APIRouter(prefix="/nexus/settings", tags=["nexus_settings"])


def get_service() -> SettingsService:
    return SettingsService()


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
    
    try:
        kill_switch.ensure_action_allowed(ctx, "settings_read")
        limiter.check_rate_limit(ctx, "settings_read")
        return service.get_surface_settings(ctx)
    except HTTPException:
        raise
    except Exception as exc:
        if "not found" in str(exc).lower():
            return error_response(code="nexus.settings_not_found", message=str(exc), status_code=404)
        return error_response(code="nexus.settings_read_failed", message=str(exc), status_code=500)


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
    try:
        kill_switch.ensure_action_allowed(ctx, "settings_read")
        limiter.check_rate_limit(ctx, "settings_read")
        return service.get_apps(ctx)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.apps_read_failed", message=str(exc), status_code=500)


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
    try:
        kill_switch.ensure_action_allowed(ctx, "settings_read")
        limiter.check_rate_limit(ctx, "settings_read")
        return service.get_connectors(ctx)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.connectors_read_failed", message=str(exc), status_code=500)
