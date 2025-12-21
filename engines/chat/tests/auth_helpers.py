import os
import uuid
from typing import Dict, List, Tuple

from engines.identity.jwt_service import default_jwt_service


_DEFAULT_SECRET = "chat-secret"

os.environ.setdefault("AUTH_JWT_SIGNING", _DEFAULT_SECRET)
os.environ.setdefault("APP_ENV", "dev")


def _claims(
    tenant_id: str,
    user_id: str,
    tenant_ids: List[str] | None = None,
    default_tenant_id: str | None = None,
    role_map: Dict[str, str] | None = None,
) -> Dict[str, object]:
    tenant_ids = tenant_ids or [tenant_id]
    default_tenant_id = default_tenant_id or tenant_id
    role_map = role_map or {tenant_id: "member"}
    return {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": tenant_ids,
        "default_tenant_id": default_tenant_id,
        "role_map": role_map,
    }


def issue_auth_token(
    tenant_id: str = "t_demo",
    user_id: str = "u_test",
    tenant_ids: List[str] | None = None,
    default_tenant_id: str | None = None,
    role_map: Dict[str, str] | None = None,
) -> str:
    svc = default_jwt_service()
    return svc.issue_token(_claims(tenant_id, user_id, tenant_ids, default_tenant_id, role_map))


def auth_headers(
    tenant_id: str = "t_demo",
    env: str = "dev",
    user_id: str = "u_test",
    request_id: str | None = None,
) -> Dict[str, str]:
    token = issue_auth_token(tenant_id=tenant_id, user_id=user_id)
    rid = request_id or uuid.uuid4().hex
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Env": env,
        "X-User-Id": user_id,
        "X-Request-Id": rid,
    }


def auth_header_items(
    tenant_id: str = "t_demo",
    env: str = "dev",
    user_id: str = "u_test",
    request_id: str | None = None,
) -> List[Tuple[str, str]]:
    headers = auth_headers(tenant_id=tenant_id, env=env, user_id=user_id, request_id=request_id)
    return list(headers.items())
