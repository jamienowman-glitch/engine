from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Path

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.config_store.service import (
    ConfigPayload,
    ConfigService,
    EffectiveConfigPayload,
    get_config_service,
)

ALLOWED_SCOPES = {"system", "tenant", "surface"}

router = APIRouter(prefix="/config", tags=["config"])


def _require_membership(auth, context: RequestContext) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="config_store",
        )


def _resolve_scope_identifier(scope: str, context: RequestContext) -> str:
    if scope == "system":
        return "system"
    if scope == "tenant":
        return context.tenant_id
    if scope == "surface":
        surface = context.surface_id
        if not surface:
            error_response(
                code="config.surface_id_required",
                message="Surface identifier is required for surface scope",
                status_code=400,
                resource_kind="config_store",
            )
        return surface
    error_response(
        code="config.invalid_scope",
        message=f"Scope must be one of {sorted(ALLOWED_SCOPES)}",
        status_code=400,
        resource_kind="config_store",
    )
    return "invalid"


class ConfigRequest(BaseModel):
    version: int
    values: Dict[str, Any]


@router.get("/effective", response_model=EffectiveConfigPayload)
def get_effective_config(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: ConfigService = Depends(get_config_service),
) -> EffectiveConfigPayload:
    """Return the deterministic overlay of surface → tenant → system config values."""
    _require_membership(auth, context)
    return service.get_effective_config(context)


@router.get("/{scope}", response_model=ConfigPayload)
def get_config(
    scope: str = Path(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: ConfigService = Depends(get_config_service),
) -> ConfigPayload:
    _require_membership(auth, context)
    identifier = _resolve_scope_identifier(scope, context)
    return service.get_config(context, scope, identifier)


@router.put("/{scope}", response_model=ConfigPayload)
def put_config(
    payload: ConfigRequest,
    scope: str = Path(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: ConfigService = Depends(get_config_service),
) -> ConfigPayload:
    _require_membership(auth, context)
    identifier = _resolve_scope_identifier(scope, context)
    try:
        return service.save_config(context, scope, identifier, payload.version, payload.values)
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="config.save_failed",
            message=str(exc),
            status_code=500,
            resource_kind="config_store",
        )
