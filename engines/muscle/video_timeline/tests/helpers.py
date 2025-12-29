from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext


def _default_context(
    tenant_id: str = "t_test",
    env: str = "dev",
    project_id: str = "p_internal",
) -> RequestContext:
    return RequestContext(tenant_id=tenant_id, env=env, project_id=project_id)


def _default_auth_context(tenant_id: str = "t_test") -> AuthContext:
    return AuthContext(
        user_id="timeline_user",
        email="timeline@example.com",
        tenant_ids=[tenant_id],
        default_tenant_id=tenant_id,
        role_map={tenant_id: "owner"},
    )


def make_timeline_client(
    *,
    tenant_id: str = "t_test",
    env: str = "dev",
    project_id: str = "p_internal",
    context: Optional[RequestContext] = None,
    auth_context: Optional[AuthContext] = None,
) -> TestClient:
    app = create_app()
    ctx = context or _default_context(tenant_id=tenant_id, env=env, project_id=project_id)
    auth = auth_context or _default_auth_context(ctx.tenant_id)
    app.dependency_overrides[get_request_context] = lambda: ctx
    app.dependency_overrides[get_auth_context] = lambda: auth
    return TestClient(app)
