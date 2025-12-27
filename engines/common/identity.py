"""Shared identity helpers and FastAPI context builder."""
from __future__ import annotations

import json
import uuid
from typing import Literal, Optional

from fastapi import Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

VALID_TENANT = r"^t_[a-z0-9_-]+$"
VALID_ENVS = {"dev", "staging", "prod", "stage"}


def _normalize_env(value: str) -> str:
    env_norm = value.lower()
    if env_norm not in VALID_ENVS:
        raise ValueError(f"env must be one of {sorted(VALID_ENVS)}")
    return "staging" if env_norm == "stage" else env_norm


class RequestContext(BaseModel):
    """Standard tenant/env/user context for requests."""

    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tenant_id: str = Field(..., pattern=VALID_TENANT)
    env: Literal["dev", "staging", "prod", "stage"]
    project_id: str = Field(default_factory=lambda: "p_internal", description="Project metadata for routed workloads")
    surface_id: Optional[str] = Field(default=None, description="Surface ID (content container)")
    app_id: Optional[str] = Field(default=None, description="App ID (application unit)")
    user_id: Optional[str] = Field(default=None, description="End-user or agent ID")
    membership_role: Optional[Literal["owner", "admin", "member", "viewer"]] = None
    auth_subject: Optional[str] = None
    is_system: bool = False

    @field_validator("env", mode="before")
    def _env_allowed(cls, v: str) -> str:
        return _normalize_env(v)


async def get_request_context(
    request: Request,
    header_tenant: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    header_env: Optional[str] = Header(default=None, alias="X-Env"),
    header_project: Optional[str] = Header(default=None, alias="X-Project-Id"),
    header_surface: Optional[str] = Header(default=None, alias="X-Surface-Id"),
    header_app: Optional[str] = Header(default=None, alias="X-App-Id"),
    header_user: Optional[str] = Header(default=None, alias="X-User-Id"),
    header_role: Optional[str] = Header(default=None, alias="X-Membership-Role"),
    header_request_id: Optional[str] = Header(default=None, alias="X-Request-Id"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    # Back-compat query params (will remain until JWT parsing is wired)
    query_tenant: Optional[str] = Query(default=None, alias="tenant_id"),
    query_env: Optional[str] = Query(default=None, alias="env"),
    query_user: Optional[str] = Query(default=None, alias="user_id"),
    query_project: Optional[str] = Query(default=None, alias="project_id"),
    query_surface: Optional[str] = Query(default=None, alias="surface_id"),
    query_app: Optional[str] = Query(default=None, alias="app_id"),
) -> RequestContext:
    """Build a RequestContext from headers/query/body payload.

    Project information is required via `X-Project-Id` or `project_id`.
    Surface and App default to tenant defaults if not provided; error if defaults don't exist.
    Request-ID is always generated if not provided.
    """
    tenant = header_tenant or query_tenant
    env = header_env or query_env
    project_id = header_project or query_project
    surface_id = header_surface or query_surface
    app_id = header_app or query_app
    user = header_user or query_user
    auth_ctx = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            from engines.identity.jwt_service import default_jwt_service

            auth_ctx = default_jwt_service().decode_token(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"invalid token: {exc}")
    # Fallback to body (JSON) for POST/PUT routes that still send tenant/env in payload.
    needs_body = not tenant or not env or not project_id or not user
    if needs_body:
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_json = json.loads(body_bytes.decode())
                if not tenant:
                    tenant = body_json.get("tenant_id")
                if not env:
                    env = body_json.get("env")
                if not user:
                    user = body_json.get("user_id")
                if not project_id:
                    project_id = body_json.get("project_id")
                if not surface_id:
                    surface_id = body_json.get("surface_id")
                if not app_id:
                    app_id = body_json.get("app_id")
        except Exception:
            # Best-effort only; real auth will arrive later.
            pass
    if auth_ctx:
        # If tenant not provided, fall back to default_tenant_id from token
        if not tenant:
            tenant = auth_ctx.default_tenant_id
        # Ensure tenant is part of memberships
        if tenant and tenant not in auth_ctx.tenant_ids:
            raise HTTPException(status_code=403, detail="tenant mismatch with token")
        # Prefer user_id from token
        user = auth_ctx.user_id or user
        # If no explicit role header, use role from token for this tenant
        if tenant and not header_role:
            header_role = auth_ctx.role_map.get(tenant)
    if not tenant or not env:
        raise HTTPException(status_code=400, detail="tenant_id and env are required")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    
    # If surface_id or app_id are missing, try to fetch defaults from control-plane
    if not surface_id or not app_id:
        from engines.identity.state import identity_repo
        if not surface_id:
            surfaces = identity_repo.list_surfaces_for_tenant(tenant)
            # Use the first surface as default (ideally sorted by name/creation)
            if surfaces:
                surface_id = surfaces[0].id
            else:
                raise HTTPException(status_code=400, detail="surface_id required and no default found")
        if not app_id:
            apps = identity_repo.list_apps_for_tenant(tenant)
            # Use the first app as default
            if apps:
                app_id = apps[0].id
            else:
                raise HTTPException(status_code=400, detail="app_id required and no default found")
    
    # request_id is always generated if not provided
    req_id = header_request_id or request.headers.get("X-Request-ID") or uuid.uuid4().hex
    return RequestContext(
        request_id=req_id,
        tenant_id=tenant,
        env=env,
        user_id=user,
        membership_role=header_role,  # optional; authoritative once JWT arrives
        auth_subject=None,
        is_system=False,
        project_id=project_id,
        surface_id=surface_id,
        app_id=app_id,
    )


def assert_context_matches(
    context: RequestContext,
    tenant_id: Optional[str] = None,
    env: Optional[str] = None,
    project_id: Optional[str] = None,
    surface_id: Optional[str] = None,
    app_id: Optional[str] = None,
) -> None:
    """Ensure caller-supplied tenant/env/project/surface/app match the resolved context."""
    if tenant_id and tenant_id != context.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id mismatch with request context")
    if env:
        try:
            env_normalized = _normalize_env(env)
        except ValueError:
            raise HTTPException(status_code=400, detail="env mismatch with request context")
        if env_normalized != context.env:
            raise HTTPException(status_code=400, detail="env mismatch with request context")
    if project_id and project_id != context.project_id:
        raise HTTPException(status_code=400, detail="project_id mismatch with request context")
    if surface_id and surface_id != context.surface_id:
        raise HTTPException(status_code=400, detail="surface_id mismatch with request context")
    if app_id and app_id != context.app_id:
        raise HTTPException(status_code=400, detail="app_id mismatch with request context")
