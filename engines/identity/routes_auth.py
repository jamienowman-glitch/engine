from __future__ import annotations

import os
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from engines.identity.auth_schemas import AuthTokenResponse, LoginRequest, SignupRequest
from engines.identity.jwt_service import default_jwt_service
from engines.identity.auth import get_auth_context
from engines.identity.passwords import hash_password, verify_password
from engines.identity.models import Tenant, TenantMembership, User, TenantKeyConfig, TenantMode, ControlPlaneProject
from engines.identity.state import identity_repo, set_identity_repo
from uuid import uuid4


router = APIRouter(prefix="/auth", tags=["auth"])


def _create_tenant(name: str, created_by: Optional[str] = None, tenant_id: Optional[str] = None) -> Tenant:
    if not tenant_id:
        tenant_id = f"t_{uuid4().hex}"
    tenant = Tenant(id=tenant_id, name=name, created_by=created_by)
    identity_repo.create_tenant(tenant)
    return tenant


@router.post("/signup", response_model=AuthTokenResponse)
def signup(payload: SignupRequest):
    _ensure_jwt_config()
    if identity_repo.get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="user already exists")
    pwd_hash, salt = hash_password(payload.password)
    user = User(email=payload.email, display_name=payload.display_name, password_hash=f"{pwd_hash}:{salt}")
    identity_repo.create_user(user)
    tenant = None
    if payload.tenant_name:
        tenant = _create_tenant(payload.tenant_name, created_by=user.id)
        identity_repo.create_membership(
            TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner")
        )
        
        # Phase 0 Closeout: Create default surface, app, and project
        from engines.identity.models import Surface, App
        
        # Create default surface
        default_surface = Surface(
            tenant_id=tenant.id,
            name="default",
            description="Default surface created on tenant signup",
            created_by=user.id,
        )
        identity_repo.create_surface(default_surface)
        
        # Create default app
        default_app = App(
            tenant_id=tenant.id,
            name="default",
            app_type="web",
            description="Default app created on tenant signup",
            created_by=user.id,
        )
        identity_repo.create_app(default_app)
        
        # Create default project record in control-plane
        default_project = ControlPlaneProject(
            tenant_id=tenant.id,
            env="dev",
            project_id="default",
            name="Default Project",
            description="Default project created on tenant signup",
            default_surface_id=default_surface.id,
            default_app_id=default_app.id,
            created_by=user.id,
        )
        identity_repo.create_project(default_project)
    
    memberships = identity_repo.list_memberships_for_user(user.id)
    token = _issue_for_user(user, memberships)
    return _token_response(user, memberships, tenant)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest):
    _ensure_jwt_config()
    user = identity_repo.get_user_by_email(payload.email)
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="invalid credentials")
    try:
        stored_hash, salt = user.password_hash.split(":")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not verify_password(payload.password, stored_hash, salt):
        raise HTTPException(status_code=401, detail="invalid credentials")
    memberships = identity_repo.list_memberships_for_user(user.id)
    return _token_response(user, memberships, None)


@router.get("/me")
def me(auth=Depends(get_auth_context)):
    return auth


@router.post("/refresh", response_model=AuthTokenResponse)
def refresh(auth=Depends(get_auth_context)):
    user = identity_repo.get_user(auth.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    memberships = identity_repo.list_memberships_for_user(user.id)
    return _token_response(user, memberships, None)


@router.get("/bootstrap")
def bootstrap(auth=Depends(get_auth_context)):
    """Return auth context after ensuring user/tenant bootstrap (for Cognito)."""
    return auth


@router.post("/bootstrap/tenants")
def bootstrap_tenants(x_system_key: str = Header(..., alias="X-System-Key")):
    """
    Idempotent bootstrap for system tenant and control-plane modes.
    Requires SYSTEM_BOOTSTRAP_KEY env var match.
    """
    expected_key = os.getenv("SYSTEM_BOOTSTRAP_KEY")
    if not expected_key or x_system_key != expected_key:
        raise HTTPException(status_code=403, detail="invalid system key")

    created = []

    # Tenant-0: System
    t0_id = "t_system"
    if not identity_repo.get_tenant(t0_id):
        _create_tenant(name="System Control Plane", tenant_id=t0_id)
        created.append(t0_id)

    # Seed control-plane modes (owned by t_system)
    _seed_tenant_modes()
    
    # Seed default surface/app for t_system if not present
    _seed_system_defaults(t0_id)

    return {"status": "ok", "created": created}


def _seed_tenant_modes():
    """Idempotent seeding of default tenant modes (enterprise, saas, lab)."""
    default_modes = [
        ("enterprise", "Enterprise deployment mode"),
        ("saas", "SaaS deployment mode"),
        ("lab", "Lab/experimental deployment mode"),
    ]
    for mode_name, description in default_modes:
        if not identity_repo.get_tenant_mode_by_name(mode_name):
            mode = TenantMode(name=mode_name, description=description)
            identity_repo.create_tenant_mode(mode)


def _seed_system_defaults(tenant_id: str) -> None:
    """Idempotent seeding of default surface/app for t_system."""
    from engines.identity.models import Surface, App
    
    # Check if default surface already exists
    surfaces = identity_repo.list_surfaces_for_tenant(tenant_id)
    if not surfaces:
        default_surface = Surface(
            tenant_id=tenant_id,
            name="default",
            description="System default surface",
        )
        identity_repo.create_surface(default_surface)
    
    # Check if default app already exists
    apps = identity_repo.list_apps_for_tenant(tenant_id)
    if not apps:
        default_app = App(
            tenant_id=tenant_id,
            name="default",
            app_type="backend",
            description="System default app",
        )
        identity_repo.create_app(default_app)



def _issue_for_user(user: User, memberships) -> str:
    svc = default_jwt_service()
    tenant_ids = [m.tenant_id for m in memberships]
    role_map: Dict[str, str] = {m.tenant_id: m.role for m in memberships}
    claims = {
        "sub": user.id,
        "email": user.email,
        "tenant_ids": tenant_ids,
        "default_tenant_id": tenant_ids[0] if tenant_ids else "",
        "role_map": role_map,
    }
    return svc.issue_token(claims)


def _token_response(user: User, memberships, tenant: Optional[Tenant]) -> AuthTokenResponse:
    token = _issue_for_user(user, memberships)
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user={"id": user.id, "email": user.email, "display_name": user.display_name, "avatar_url": user.avatar_url},
        tenant=tenant.model_dump() if tenant else None,
        memberships=[m.model_dump() for m in memberships],
    )


def _ensure_jwt_config():
    if identity_repo.get_key_config("system", "prod", "auth_jwt_signing"):
        return
    # Dev-friendly default pointing to env var fallback
    identity_repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="auth_jwt_signing",
            provider="system",
            secret_name="AUTH_JWT_SIGNING",
        )
    )
