"""
Tests for RequestContext Gate 1: Mode-only enforcement.
"""

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from fastapi import FastAPI

from engines.common.identity import RequestContext, RequestContextBuilder


class TestRequestContextValidation:
    """Test RequestContext creation and validation."""
    
    def test_valid_context_creation(self):
        """Valid context with required fields."""
        ctx = RequestContext(
            tenant_id="t_acme",
            mode="saas",
            project_id="proj_123",
            request_id="req_abc"
        )
        assert ctx.tenant_id == "t_acme"
        assert ctx.mode == "saas"
        assert ctx.project_id == "proj_123"
    
    def test_missing_tenant_id(self):
        """Missing tenant_id raises ValueError."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            RequestContext(tenant_id="", mode="saas", project_id="p1")
    
    def test_invalid_tenant_id_format(self):
        """Tenant_id must match ^t_[a-z0-9_-]+$."""
        with pytest.raises(ValueError, match="tenant_id must match pattern"):
            RequestContext(
                tenant_id="acme",  # missing t_ prefix
                mode="saas",
                project_id="p1"
            )
    
    def test_missing_mode(self):
        """Missing mode raises ValueError."""
        with pytest.raises(ValueError, match="mode is required"):
            RequestContext(
                tenant_id="t_acme",
                mode="",
                project_id="p1"
            )
    
    def test_invalid_mode_value(self):
        """Mode must be saas|enterprise|lab exactly."""
        invalid_modes = ["dev", "staging", "prod", "production", "stage", "invalid"]
        for invalid_mode in invalid_modes:
            with pytest.raises(ValueError, match="mode must be one of"):
                RequestContext(
                    tenant_id="t_acme",
                    mode=invalid_mode,
                    project_id="p1"
                )
    
    def test_valid_modes(self):
        """Valid modes: saas, enterprise, lab."""
        for valid_mode in ["saas", "enterprise", "lab"]:
            ctx = RequestContext(
                tenant_id="t_acme",
                mode=valid_mode,
                project_id="p1"
            )
            assert ctx.mode == valid_mode
    
    def test_missing_project_id(self):
        """Missing project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id is required"):
            RequestContext(
                tenant_id="t_acme",
                mode="saas",
                project_id=""
            )


class TestRequestContextBuilderFromHeaders:
    """Test RequestContextBuilder.from_headers (core builder)."""
    
    def test_minimal_valid_headers(self):
        """Valid headers with required fields only."""
        headers = {
            "X-Mode": "saas",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "proj_123"
        }
        ctx = RequestContextBuilder.from_headers(headers)
        assert ctx.mode == "saas"
        assert ctx.tenant_id == "t_acme"
        assert ctx.project_id == "proj_123"
        assert ctx.request_id  # auto-generated
    
    def test_case_insensitive_headers(self):
        """Header names are case-insensitive."""
        headers = {
            "x-mode": "enterprise",
            "x-tenant-id": "t_test",
            "x-project-id": "p1"
        }
        ctx = RequestContextBuilder.from_headers(headers)
        assert ctx.mode == "enterprise"
        assert ctx.tenant_id == "t_test"
    
    def test_missing_mode_header(self):
        """Missing X-Mode raises ValueError."""
        headers = {
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "p1"
        }
        with pytest.raises(ValueError, match="X-Mode header is required"):
            RequestContextBuilder.from_headers(headers)
    
    def test_invalid_mode_value_in_headers(self):
        """Invalid mode value raises ValueError."""
        headers = {
            "X-Mode": "dev",  # LEGACY, must reject
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "p1"
        }
        with pytest.raises(ValueError, match="X-Mode must be one of"):
            RequestContextBuilder.from_headers(headers)
    
    def test_reject_legacy_env_values(self):
        """X-Mode with legacy env values rejected."""
        legacy_values = ["dev", "development", "staging", "stage", "prod", "production"]
        for legacy_value in legacy_values:
            headers = {
                "X-Mode": legacy_value,
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "p1"
            }
            with pytest.raises(ValueError, match="X-Mode must be one of"):
                RequestContextBuilder.from_headers(headers)
    
    def test_reject_x_env_header(self):
        """X-Env header present → 400 error."""
        headers = {
            "X-Env": "staging",  # FORBIDDEN
            "X-Mode": "saas",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "p1"
        }
        with pytest.raises(ValueError, match="X-Env header is not allowed"):
            RequestContextBuilder.from_headers(headers)
    
    def test_reject_x_env_case_insensitive(self):
        """X-Env rejection is case-insensitive."""
        for env_key in ["X-Env", "x-env", "x-ENV", "X-env"]:
            headers = {
                env_key: "prod",
                "X-Mode": "saas",
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "p1"
            }
            with pytest.raises(ValueError, match="X-Env header is not allowed"):
                RequestContextBuilder.from_headers(headers)
    
    def test_missing_tenant_id(self):
        """Missing X-Tenant-Id raises ValueError."""
        headers = {
            "X-Mode": "saas",
            "X-Project-Id": "p1"
        }
        with pytest.raises(ValueError, match="X-Tenant-Id header is required"):
            RequestContextBuilder.from_headers(headers)
    
    def test_missing_project_id(self):
        """Missing X-Project-Id raises ValueError."""
        headers = {
            "X-Mode": "saas",
            "X-Tenant-Id": "t_acme"
        }
        with pytest.raises(ValueError, match="X-Project-Id header is required"):
            RequestContextBuilder.from_headers(headers)
    
    def test_optional_headers_populated(self):
        """Optional headers are correctly populated."""
        headers = {
            "X-Mode": "lab",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "p1",
            "X-Surface-Id": "surf_123",
            "X-App-Id": "app_456",
            "X-User-Id": "user_789",
            "X-Request-Id": "req_abc",
            "X-Membership-Role": "admin"
        }
        ctx = RequestContextBuilder.from_headers(headers)
        assert ctx.surface_id == "surf_123"
        assert ctx.app_id == "app_456"
        assert ctx.user_id == "user_789"
        assert ctx.request_id == "req_abc"
        assert ctx.membership_role == "admin"
    
    def test_jwt_overlay(self):
        """JWT payload overlays tenant_id/user_id/role."""
        headers = {
            "X-Mode": "saas",
            "X-Tenant-Id": "t_acme",
            "X-Project-Id": "p1",
            "X-User-Id": "client_user"  # will be overridden
        }
        jwt_payload = {
            "tenant_id": "t_jwt_tenant",
            "user_id": "jwt_user",
            "role": "owner"
        }
        ctx = RequestContextBuilder.from_headers(headers, jwt_payload)
        assert ctx.tenant_id == "t_jwt_tenant"
        assert ctx.user_id == "jwt_user"
        assert ctx.membership_role == "owner"
    
    def test_t_system_allowed(self):
        """t_system is the only hardcoded allowed tenant."""
        headers = {
            "X-Mode": "lab",
            "X-Tenant-Id": "t_system",
            "X-Project-Id": "p_bootstrap"
        }
        ctx = RequestContextBuilder.from_headers(headers)
        assert ctx.tenant_id == "t_system"


class TestRequestContextBuilderFromRequest:
    """Test RequestContextBuilder.from_request (FastAPI Request)."""
    
    def test_valid_request(self):
        """Valid FastAPI request."""
        # Create a minimal FastAPI app for testing
        app = FastAPI()
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            ctx = RequestContextBuilder.from_request(request)
            return {"mode": ctx.mode, "tenant": ctx.tenant_id}
        
        client = TestClient(app)
        response = client.post(
            "/test",
            headers={
                "X-Mode": "enterprise",
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "proj_x"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "enterprise"
        assert data["tenant"] == "t_acme"
    
    def test_request_reject_x_env(self):
        """FastAPI request with X-Env is rejected."""
        app = FastAPI()
        
        @app.post("/test")
        async def test_endpoint(request: Request):
            try:
                ctx = RequestContextBuilder.from_request(request)
                return {"ok": True}
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
        
        client = TestClient(app)
        response = client.post(
            "/test",
            headers={
                "X-Env": "staging",
                "X-Mode": "saas",
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "p1"
            }
        )
        assert response.status_code == 400
        assert "X-Env" in response.json()["error"]


class TestMinimalEndpoint:
    """Test a minimal endpoint using RequestContext."""
    
    def test_minimal_endpoint_with_mode_context(self):
        """Minimal endpoint that accepts and validates RequestContext."""
        app = FastAPI()
        
        @app.post("/echo-context")
        async def echo_context(request: Request):
            try:
                ctx = RequestContextBuilder.from_request(request)
                return {
                    "tenant_id": ctx.tenant_id,
                    "mode": ctx.mode,
                    "project_id": ctx.project_id,
                    "request_id": ctx.request_id
                }
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
        
        client = TestClient(app)
        
        # Valid request passes
        response = client.post(
            "/echo-context",
            headers={
                "X-Mode": "saas",
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "proj_123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "saas"
        assert data["tenant_id"] == "t_acme"
        assert data["project_id"] == "proj_123"
        
        # Missing mode fails
        response = client.post(
            "/echo-context",
            headers={
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "proj_123"
            }
        )
        assert response.status_code == 400
        assert "X-Mode" in response.json()["error"]
        
        # Invalid mode fails
        response = client.post(
            "/echo-context",
            headers={
                "X-Mode": "dev",  # legacy
                "X-Tenant-Id": "t_acme",
                "X-Project-Id": "proj_123"
            }
        )
        assert response.status_code == 400
        assert "X-Mode must be one of" in response.json()["error"]
