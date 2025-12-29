from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext


async def _test_request_context(request: Request) -> RequestContext:
    tenant = request.headers.get("X-Tenant-Id") or request.query_params.get("tenant_id")
    env = request.headers.get("X-Env") or request.query_params.get("env")
    project_id = request.headers.get("X-Project-Id") or request.query_params.get("project_id")
    user = request.headers.get("X-User-Id") or request.query_params.get("user_id")

    if not (tenant and env and project_id):
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_json = json.loads(body_bytes.decode())
                tenant = tenant or body_json.get("tenant_id")
                env = env or body_json.get("env")
                project_id = project_id or body_json.get("project_id")
                user = user or body_json.get("user_id")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    if not tenant or not env:
        raise HTTPException(status_code=400, detail="tenant_id and env are required")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    return RequestContext.model_construct(
        request_id=request_id,
        tenant_id=tenant,
        env=env,
        project_id=project_id,
        user_id=user,
    )


async def _test_auth_context(request: Request) -> AuthContext:
    tenant = request.headers.get("X-Tenant-Id") or request.query_params.get("tenant_id")
    if not tenant:
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_json = json.loads(body_bytes.decode())
                tenant = body_json.get("tenant_id")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    tenant = tenant or "t_test"
    return AuthContext(
        user_id="render_user",
        email="render@example.com",
        tenant_ids=[tenant],
        default_tenant_id=tenant,
        role_map={tenant: "owner"},
    )


def make_video_render_client(
    *,
    context: Optional[RequestContext] = None,
    auth_context: Optional[AuthContext] = None,
) -> TestClient:
    app = create_app()
    if context is not None:
        app.dependency_overrides[get_request_context] = lambda: context
    else:
        app.dependency_overrides[get_request_context] = _test_request_context

    if auth_context is not None:
        app.dependency_overrides[get_auth_context] = lambda: auth_context
    else:
        app.dependency_overrides[get_auth_context] = _test_auth_context

    return TestClient(app)
