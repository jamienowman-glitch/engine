"""Auth dependency and role enforcement."""
from __future__ import annotations

from typing import List, Optional

from fastapi import Depends, HTTPException, Header

from engines.identity.bootstrap import bootstrap_auth_context
from engines.identity.cognito import CognitoVerificationError, get_cognito_verifier
from engines.identity.jwt_service import AuthContext, default_jwt_service


def get_auth_context(authorization: Optional[str] = Header(default=None)) -> AuthContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    primary_error: Optional[Exception] = None
    try:
        service = default_jwt_service()
        ctx = service.decode_token(token)
        return bootstrap_auth_context(ctx)
    except Exception as exc:
        primary_error = exc

    verifier = get_cognito_verifier()
    if verifier:
        try:
            ctx = verifier.verify(token)
            return bootstrap_auth_context(ctx)
        except CognitoVerificationError as exc:
            raise HTTPException(status_code=401, detail=f"invalid cognito token: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"invalid cognito token: {exc}") from exc

    raise HTTPException(status_code=401, detail=f"invalid token: {primary_error}") from primary_error


def get_optional_auth_context(authorization: Optional[str] = Header(default=None)) -> Optional[AuthContext]:
    if not authorization:
        return None
    try:
        return get_auth_context(authorization)
    except HTTPException:
        raise


def require_tenant_role(ctx: AuthContext, tenant_id: str, allowed_roles: List[str]) -> None:
    role = ctx.role_map.get(tenant_id)
    if not role or role not in allowed_roles:
        raise HTTPException(status_code=403, detail="insufficient role for tenant")


def require_tenant_membership(ctx: AuthContext, tenant_id: str) -> None:
    if tenant_id not in ctx.tenant_ids:
        raise HTTPException(status_code=403, detail="tenant membership required")
