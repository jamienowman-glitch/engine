import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from engines.canvas_stream.router import router as sse_router
from engines.canvas_stream.service import publish_canvas_event
from engines.identity.auth import get_auth_context
from engines.common.identity import get_request_context, RequestContext
from engines.identity.jwt_service import AuthContext

from fastapi import FastAPI, Depends

app = FastAPI()
app.include_router(sse_router)

client = TestClient(app)

# Mocks
async def mock_auth_ctx():
    return AuthContext(
        user_id="u_test",
        email="test@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "member"}
    )

async def mock_req_ctx():
    return RequestContext(
        tenant_id="t_test", 
        env="dev",
        user_id="u_test"
    )

app.dependency_overrides[get_auth_context] = mock_auth_ctx
app.dependency_overrides[get_request_context] = mock_req_ctx

def test_sse_connect_and_stream():
    # Publish event beforehand
    canvas_id = "canvas-1"
    evt = publish_canvas_event(canvas_id, "gesture", {"x": 10}, "u_test", "t_test")
    
    # TestClient stream=True
    with client.stream("GET", f"/sse/canvas/{canvas_id}", headers={"Last-Event-ID": evt.id}) as response:
        assert response.status_code == 200
        # Check first line
        chunk = next(response.iter_lines())
        assert chunk.startswith("id: ")
        
        chunk = next(response.iter_lines())
        assert chunk == "event: canvas_update"

def test_stream_canvas_auto_registers():
    """
    L1-T3: Verify that publishing an event registers the canvas, allowing SSE access.
    """
    canvas_id = "canvas-auto-reg-1"
    tenant_id = "t_test"
    
    # 1. Publish (should register)
    publish_canvas_event(canvas_id, "commit", {"foo": "bar"}, "u_test", tenant_id)
    
    # 2. Connect SSE (should pass 404/403 check if registered)
    # Implicitly uses mock_req_ctx with t_test
    with client.stream("GET", f"/sse/canvas/{canvas_id}") as response:
        assert response.status_code == 200
        first = next(response.iter_lines())
        assert first.startswith("id: ")

def test_sse_tenant_mismatch():
    async def bad_req_ctx():
        return RequestContext(tenant_id="t_other", env="dev")
    
    app.dependency_overrides[get_request_context] = bad_req_ctx
    
    response = client.get("/sse/canvas/canvas-1")
    assert response.status_code == 403
    
    # Restore override
    app.dependency_overrides[get_request_context] = mock_req_ctx
