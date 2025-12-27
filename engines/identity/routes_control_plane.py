"""Control-plane CRUD routes for Surface, App, and Project primitives (Phase 0 closeout)."""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from engines.identity.auth import get_auth_context, AuthContext, require_tenant_membership
from engines.identity.models import Surface, App, ControlPlaneProject
from engines.identity.state import identity_repo
from engines.common.identity import get_request_context, RequestContext


router = APIRouter(prefix="/control-plane", tags=["control-plane"])


# ===== Surface Routes =====

@router.post("/surfaces", response_model=Surface)
def create_surface(
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create a new Surface under the authenticated user's tenant."""
    require_tenant_membership(auth, ctx.tenant_id)
    surface = Surface(
        tenant_id=ctx.tenant_id,
        name=name,
        slug=slug,
        description=description,
        created_by=auth.user_id,
    )
    return identity_repo.create_surface(surface)


@router.get("/surfaces/{surface_id}", response_model=Optional[Surface])
def get_surface(
    surface_id: str,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get a Surface by ID (must belong to user's tenant)."""
    require_tenant_membership(auth, ctx.tenant_id)
    surface = identity_repo.get_surface(surface_id)
    if not surface:
        raise HTTPException(status_code=404, detail="Surface not found")
    if surface.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return surface


@router.get("/surfaces", response_model=list[Surface])
def list_surfaces(
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """List all Surfaces under the authenticated user's tenant."""
    require_tenant_membership(auth, ctx.tenant_id)
    return identity_repo.list_surfaces_for_tenant(ctx.tenant_id)


# ===== App Routes =====

@router.post("/apps", response_model=App)
def create_app(
    name: str,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    app_type: str = "web",
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create a new App under the authenticated user's tenant."""
    require_tenant_membership(auth, ctx.tenant_id)
    app = App(
        tenant_id=ctx.tenant_id,
        name=name,
        slug=slug,
        description=description,
        app_type=app_type,
        created_by=auth.user_id,
    )
    return identity_repo.create_app(app)


@router.get("/apps/{app_id}", response_model=Optional[App])
def get_app(
    app_id: str,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get an App by ID (must belong to user's tenant)."""
    require_tenant_membership(auth, ctx.tenant_id)
    app = identity_repo.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    if app.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return app


@router.get("/apps", response_model=list[App])
def list_apps(
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """List all Apps under the authenticated user's tenant."""
    require_tenant_membership(auth, ctx.tenant_id)
    return identity_repo.list_apps_for_tenant(ctx.tenant_id)


# ===== Project Routes =====

@router.post("/projects", response_model=ControlPlaneProject)
def create_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    default_surface_id: Optional[str] = None,
    default_app_id: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """Create a new Project record in the control-plane."""
    require_tenant_membership(auth, ctx.tenant_id)
    project = ControlPlaneProject(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        project_id=project_id,
        name=name,
        description=description,
        default_surface_id=default_surface_id,
        default_app_id=default_app_id,
        created_by=auth.user_id,
    )
    return identity_repo.create_project(project)


@router.get("/projects/{project_id}", response_model=Optional[ControlPlaneProject])
def get_project(
    project_id: str,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get a Project record by ID (must belong to user's tenant/env)."""
    require_tenant_membership(auth, ctx.tenant_id)
    project = identity_repo.get_project(ctx.tenant_id, ctx.env, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects", response_model=list[ControlPlaneProject])
def list_projects(
    env: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    """List all Projects under the authenticated user's tenant (optionally filtered by env)."""
    require_tenant_membership(auth, ctx.tenant_id)
    return identity_repo.list_projects_for_tenant(ctx.tenant_id, env=env or ctx.env)
