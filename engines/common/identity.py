"""Shared identity helpers and FastAPI context builder with mode-only enforcement."""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, Query, Request
from engines.common.error_envelope import error_response

VALID_TENANT_PATTERN = re.compile(r"^t_[a-z0-9_-]+$")
VALID_MODES = frozenset({"saas", "enterprise", "lab"})
LEGACY_ENV_VALUES = frozenset({
    "dev",
    "development",
    "staging",
    "stage",
    "prod",
    "production",
})


def _build_mode_segment(mode_value: str) -> str:
    return mode_value.lower()


def _reject_env_header(headers: Dict[str, Any]) -> None:
    for key in headers.keys():
        if key.lower() == "x-env":
            raise ValueError("X-Env header is not allowed; use X-Mode (saas|enterprise|lab)")


def _default_env() -> str:
    env_value = os.getenv("ENV") or os.getenv("APP_ENV")
    return env_value.lower() if env_value else "dev"


@dataclass
class RequestContext:
    tenant_id: str
    env: Optional[str] = None
    project_id: str = field(default="p_internal")
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    user_id: Optional[str] = None
    membership_role: Optional[str] = None
    auth_subject: Optional[str] = None
    is_system: bool = False
    actor_id: Optional[str] = None
    canvas_id: Optional[str] = None
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace_id: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    strategy_lock_id: Optional[str] = None
    three_wise_id: Optional[str] = None
    mode: Optional[str] = None
    _raw_headers: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _mode_provided: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
        if not VALID_TENANT_PATTERN.match(self.tenant_id):
            raise ValueError(
                f"tenant_id must match pattern ^t_[a-z0-9_-]+$, got: {self.tenant_id}"
            )
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.request_id:
            raise ValueError("request_id is required")

        env_value = (self.env or _default_env()).lower()
        self.env = env_value

        mode_value = self.mode
        mode_provided = mode_value is not None
        if mode_provided:
            self._mode_provided = True
            if not mode_value:
                raise ValueError("mode is required")
        if not mode_value:
            mode_value = env_value
        if not mode_value:
            raise ValueError("mode is required")
        normalized_mode = mode_value.lower()
        if self._mode_provided and normalized_mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got: {normalized_mode}")
        self.mode = normalized_mode


class RequestContextBuilder:
    """Builder for RequestContext from HTTP headers."""

    LEGACY_ENV_VALUES = LEGACY_ENV_VALUES

    @classmethod
    def from_request(
        cls,
        request: Request,
        jwt_payload: Optional[Dict[str, Any]] = None,
    ) -> RequestContext:
        headers = {key: value for key, value in request.headers.items()}
        return cls.from_headers(headers, jwt_payload=jwt_payload)

    @classmethod
    def from_headers(
        cls,
        headers: Dict[str, str],
        jwt_payload: Optional[Dict[str, Any]] = None,
    ) -> RequestContext:
        _reject_env_header(headers)
        normalized = {key.lower(): value for key, value in headers.items()}

        mode = normalized.get("x-mode")
        if not mode:
            raise ValueError(
                "X-Mode header is required; must be one of: saas, enterprise, lab"
            )
        mode = mode.lower()
        if mode in cls.LEGACY_ENV_VALUES:
            raise ValueError(
                "X-Mode must be one of saas|enterprise|lab; legacy env values are rejected"
            )
        if mode not in VALID_MODES:
            raise ValueError(
                f"X-Mode must be one of {VALID_MODES}, got: {mode}"
            )
        tenant_id = normalized.get("x-tenant-id")
        if not tenant_id:
            raise ValueError("X-Tenant-Id header is required")
        project_id = normalized.get("x-project-id")
        if not project_id:
            raise ValueError("X-Project-Id header is required")

        request_id = normalized.get("x-request-id") or str(uuid.uuid4())
        surface_id = normalized.get("x-surface-id")
        app_id = normalized.get("x-app-id")
        user_id = normalized.get("x-user-id")
        membership_role = normalized.get("x-membership-role")
        trace_id = normalized.get("x-trace-id")
        run_id = normalized.get("x-run-id")
        step_id = normalized.get("x-step-id")
        strategy_lock_id = normalized.get("x-strategy-lock-id")
        three_wise_id = normalized.get("x-three-wise-id")

        if jwt_payload:
            tenant_id = jwt_payload.get("tenant_id") or tenant_id
            user_id = jwt_payload.get("user_id") or user_id
            membership_role = jwt_payload.get("role") or membership_role

        ctx = RequestContext(
            tenant_id=tenant_id,
            mode=mode,
            project_id=project_id,
            request_id=request_id,
            surface_id=surface_id,
            app_id=app_id,
            user_id=user_id,
            actor_id=user_id,
            membership_role=membership_role,
            trace_id=trace_id,
            run_id=run_id,
            step_id=step_id,
            strategy_lock_id=strategy_lock_id,
            three_wise_id=three_wise_id,
        )
        ctx._raw_headers = headers
        return ctx


async def get_request_context(
    request: Request,
    header_tenant: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    header_mode: Optional[str] = Header(default=None, alias="X-Mode"),
    header_project: Optional[str] = Header(default=None, alias="X-Project-Id"),
    header_surface: Optional[str] = Header(default=None, alias="X-Surface-Id"),
    header_app: Optional[str] = Header(default=None, alias="X-App-Id"),
    header_user: Optional[str] = Header(default=None, alias="X-User-Id"),
    header_role: Optional[str] = Header(default=None, alias="X-Membership-Role"),
    header_request_id: Optional[str] = Header(default=None, alias="X-Request-Id"),
    header_env: Optional[str] = Header(default=None, alias="X-Env"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    query_tenant: Optional[str] = Query(default=None, alias="tenant_id"),
    query_project: Optional[str] = Query(default=None, alias="project_id"),
    query_surface: Optional[str] = Query(default=None, alias="surface_id"),
    query_app: Optional[str] = Query(default=None, alias="app_id"),
    query_user: Optional[str] = Query(default=None, alias="user_id"),
    header_trace: Optional[str] = Header(default=None, alias="X-Trace-Id"),
    header_run: Optional[str] = Header(default=None, alias="X-Run-Id"),
    header_step: Optional[str] = Header(default=None, alias="X-Step-Id"),
    header_strategy_lock: Optional[str] = Header(default=None, alias="X-Strategy-Lock-Id"),
    header_three_wise: Optional[str] = Header(default=None, alias="X-Three-Wise-Id"),
) -> RequestContext:
    if header_env:
        raise HTTPException(
            status_code=400,
            detail="X-Env header is not allowed; use X-Mode (saas|enterprise|lab)",
        )

    tenant_id = header_tenant or query_tenant
    project_id = header_project or query_project
    surface_id = header_surface or query_surface
    app_id = header_app or query_app
    user_id = header_user or query_user
    jwt_payload = None
    auth_ctx = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            from engines.identity.jwt_service import default_jwt_service

            auth_ctx = default_jwt_service().decode_token(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"invalid token: {exc}")
        if not tenant_id:
            tenant_id = auth_ctx.default_tenant_id
        if tenant_id and tenant_id not in auth_ctx.tenant_ids:
            error_response(
                code="auth.tenant_mismatch",
                message="tenant mismatch with token",
                status_code=403,
                resource_kind="auth",
            )
        user_id = auth_ctx.user_id or user_id
        if tenant_id and not header_role:
            header_role = auth_ctx.role_map.get(tenant_id)
        jwt_payload = {}
        if auth_ctx.default_tenant_id:
            jwt_payload["tenant_id"] = auth_ctx.default_tenant_id
        if auth_ctx.user_id:
            jwt_payload["user_id"] = auth_ctx.user_id
        role = auth_ctx.role_map.get(tenant_id or auth_ctx.default_tenant_id)
        if role:
            jwt_payload["role"] = role

    body_mode = None
    needs_body = not tenant_id or not project_id
    if needs_body:
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_json = json.loads(body_bytes.decode())
                if not tenant_id:
                    tenant_id = body_json.get("tenant_id")
                if not project_id:
                    project_id = body_json.get("project_id")
                if not surface_id:
                    surface_id = body_json.get("surface_id")
                if not app_id:
                    app_id = body_json.get("app_id")
                if not user_id:
                    user_id = body_json.get("user_id")
                if not header_mode:
                    body_mode = body_json.get("mode")
        except Exception:
            pass

    headers: Dict[str, str] = {}
    if header_mode:
        headers["X-Mode"] = header_mode
    elif body_mode:
        headers["X-Mode"] = body_mode
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    if project_id:
        headers["X-Project-Id"] = project_id
    if header_request_id:
        headers["X-Request-Id"] = header_request_id
    if surface_id:
        headers["X-Surface-Id"] = surface_id
    if app_id:
        headers["X-App-Id"] = app_id
    if header_user:
        headers["X-User-Id"] = header_user
    if user_id and "X-User-Id" not in headers:
        headers["X-User-Id"] = user_id
    if header_role:
        headers["X-Membership-Role"] = header_role
    if header_trace:
        headers["X-Trace-Id"] = header_trace
    if header_run:
        headers["X-Run-Id"] = header_run
    if header_step:
        headers["X-Step-Id"] = header_step
    if header_strategy_lock:
        headers["X-Strategy-Lock-Id"] = header_strategy_lock
    if header_three_wise:
        headers["X-Three-Wise-Id"] = header_three_wise

    if "X-Mode" not in headers:
        raise HTTPException(status_code=400, detail="X-Mode header is required")

    try:
        ctx = RequestContextBuilder.from_headers(headers, jwt_payload=jwt_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not ctx.surface_id or not ctx.app_id:
        from engines.identity.state import identity_repo

        if not ctx.surface_id:
            surfaces = identity_repo.list_surfaces_for_tenant(ctx.tenant_id)
            if surfaces:
                ctx.surface_id = surfaces[0].id
            else:
                raise HTTPException(status_code=400, detail="surface_id required and no default found")
        if not ctx.app_id:
            apps = identity_repo.list_apps_for_tenant(ctx.tenant_id)
            if apps:
                ctx.app_id = apps[0].id
            else:
                raise HTTPException(status_code=400, detail="app_id required and no default found")

    return ctx


def assert_context_matches(
    context: RequestContext,
    tenant_id: Optional[str] = None,
    mode: Optional[str] = None,
    env: Optional[str] = None,
    project_id: Optional[str] = None,
    surface_id: Optional[str] = None,
    app_id: Optional[str] = None,
) -> None:
    """Ensure caller-supplied tenant/mode/project/surface/app match the resolved context."""
    if tenant_id and tenant_id != context.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id mismatch with request context")
    normalized_mode: Optional[str] = mode if mode in VALID_MODES else None
    normalized_env: Optional[str] = env
    if not normalized_env and mode and mode not in VALID_MODES:
        normalized_env = mode
    if normalized_mode and normalized_mode != context.mode:
        raise HTTPException(status_code=400, detail="mode mismatch with request context")
    if normalized_env and normalized_env != context.env:
        raise HTTPException(status_code=400, detail="env mismatch with request context")
    if project_id and project_id != context.project_id:
        raise HTTPException(status_code=400, detail="project_id mismatch with request context")
    if surface_id and surface_id != context.surface_id:
        raise HTTPException(status_code=400, detail="surface_id mismatch with request context")
    if app_id and app_id != context.app_id:
        raise HTTPException(status_code=400, detail="app_id mismatch with request context")


# ============================================================
# AUTH-01: Identity Precedence Enforcement
# ============================================================

def validate_identity_precedence(
    authenticated_context: RequestContext,
    client_supplied_tenant_id: Optional[str] = None,
    client_supplied_mode: Optional[str] = None,
    client_supplied_project_id: Optional[str] = None,
    client_supplied_user_id: Optional[str] = None,
    client_supplied_surface_id: Optional[str] = None,
    domain: str = "unknown",
) -> None:
    """Enforce server-derived identity precedence (AUTH-01).
    
    Rejects any attempt to override authenticated identity from request payload/headers.
    
    Server-derived identity sources (in precedence order):
    1. JWT token claims (highest priority)
    2. RequestContext (derived from headers)
    3. Client is NOT an identity source
    
    Args:
        authenticated_context: RequestContext from server (headers/JWT)
        client_supplied_*: Identity fields from request payload
        domain: Domain name (for audit) e.g. "event_spine", "memory_store"
    
    Raises:
        HTTPException(403): If client attempts to override authenticated identity
    
    Side effects:
        - Emits audit event on mismatch (via event_spine)
    """
    mismatches = []
    
    # Check tenant_id
    if client_supplied_tenant_id and client_supplied_tenant_id != authenticated_context.tenant_id:
        mismatches.append({
            "field": "tenant_id",
            "authenticated": authenticated_context.tenant_id,
            "attempted": client_supplied_tenant_id,
        })
    
    # Check mode
    if client_supplied_mode:
        client_mode = client_supplied_mode.lower() if client_supplied_mode else None
        if client_mode and client_mode != authenticated_context.mode:
            mismatches.append({
                "field": "mode",
                "authenticated": authenticated_context.mode,
                "attempted": client_mode,
            })
    
    # Check project_id
    if client_supplied_project_id and client_supplied_project_id != authenticated_context.project_id:
        mismatches.append({
            "field": "project_id",
            "authenticated": authenticated_context.project_id,
            "attempted": client_supplied_project_id,
        })
    
    # Check user_id
    if client_supplied_user_id and client_supplied_user_id != authenticated_context.user_id:
        mismatches.append({
            "field": "user_id",
            "authenticated": authenticated_context.user_id,
            "attempted": client_supplied_user_id,
        })
    
    # Check surface_id
    if client_supplied_surface_id and client_supplied_surface_id != authenticated_context.surface_id:
        mismatches.append({
            "field": "surface_id",
            "authenticated": authenticated_context.surface_id,
            "attempted": client_supplied_surface_id,
        })
    
    if mismatches:
        # Emit audit event on mismatch
        try:
            _emit_identity_override_audit(
                context=authenticated_context,
                domain=domain,
                mismatches=mismatches,
            )
        except Exception as e:
            # Log but don't fail if audit fails
            import logging
            logging.warning(f"Failed to emit identity override audit: {e}")
        
        # Reject with 403
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "auth.identity_override",
                "message": "Client-supplied identity does not match authenticated context",
                "mismatches": mismatches,
                "domain": domain,
            },
        )


def _emit_identity_override_audit(
    context: RequestContext,
    domain: str,
    mismatches: list,
) -> None:
    """Emit audit event for identity override attempt.
    
    Uses event_spine if available; falls back to logging.
    """
    import logging
    
    try:
        from engines.event_spine.service_reject import EventSpineServiceRejectOnMissing
        
        svc = EventSpineServiceRejectOnMissing(context)
        svc.append(
            event_type="auth_violation",
            source="auth_engine",
            run_id=context.run_id or context.request_id,
            payload={
                "violation_type": "identity_override",
                "domain": domain,
                "mismatches": mismatches,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "request_id": context.request_id,
            },
        )
    except Exception as e:
        # Fallback to logging
        logging.error(
            f"Identity override audit event failed; logging instead: {e}",
            extra={
                "violation_type": "identity_override",
                "domain": domain,
                "mismatches": mismatches,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "request_id": context.request_id,
            },
        )
