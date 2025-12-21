"""Tenant-scoped auth enforcement helpers for Nexus routes."""
from __future__ import annotations

from typing import Iterable, Optional

from engines.common.identity import RequestContext
from engines.identity.auth import AuthContext, require_tenant_membership, require_tenant_role


def enforce_tenant_context(
    ctx: RequestContext,
    auth: AuthContext,
    allowed_roles: Optional[Iterable[str]] = None,
) -> None:
    """
    Ensure the resolved RequestContext and authenticated token agree on the tenant.
    Optionally enforce that the caller holds one of the allowed roles for that tenant.
    """
    require_tenant_membership(auth, ctx.tenant_id)
    if allowed_roles:
        require_tenant_role(auth, ctx.tenant_id, list(allowed_roles))
