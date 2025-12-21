"""Bootstrap helpers for external identity providers (e.g., Cognito)."""
from __future__ import annotations

import re
from typing import Optional
from uuid import uuid4

from engines.identity import state as identity_state
from engines.identity.jwt_service import AuthContext
from engines.identity.models import Tenant, TenantMembership, User


def _repo():
    return identity_state.identity_repo


def _slugify_email(email: str) -> str:
    local = email.split("@", 1)[0] if email else ""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", local.strip().lower()).strip("-")
    return slug or "tenant"


def _unique_slug(base: str) -> str:
    candidate = base
    while _repo().get_tenant_by_slug(candidate):
        candidate = f"{base}-{uuid4().hex[:4]}"
    return candidate


def bootstrap_auth_context(ctx: AuthContext) -> AuthContext:
    """Ensure a Cognito-provided user exists with an owner membership."""
    if ctx.provider != "cognito":
        return ctx

    user = _repo().get_user(ctx.user_id)
    if not user and ctx.email:
        user = _repo().get_user_by_email(ctx.email)
    if not user:
        user = User(id=ctx.user_id, email=ctx.email)
        _repo().create_user(user)

    memberships = _repo().list_memberships_for_user(user.id)
    if not memberships:
        slug = _unique_slug(_slugify_email(ctx.email))
        tenant = Tenant(id=f"t_{uuid4().hex}", name=slug, slug=slug, created_by=user.id)
        _repo().create_tenant(tenant)
        membership = TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner")
        _repo().create_membership(membership)
        memberships = [membership]

    tenant_ids = [m.tenant_id for m in memberships]
    role_map = {m.tenant_id: m.role for m in memberships}
    default_tenant_id = ctx.default_tenant_id or (tenant_ids[0] if tenant_ids else "")
    return AuthContext(
        user_id=user.id,
        email=user.email,
        tenant_ids=tenant_ids,
        default_tenant_id=default_tenant_id,
        role_map=role_map,
        provider=ctx.provider,
        claims=ctx.claims,
    )


def invite_user_to_tenant(_inviter_id: str, _email: str, _tenant_id: str) -> None:
    """TODO: implement invite flow (placeholder only)."""
    return None
