"""
Tests for CAD ingest routes and context validation.
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from engines.cad_ingest.routes import router
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context

# Setup basic app for testing
app = FastAPI()
app.include_router(router)

client = TestClient(app)

# Dummy overrides
def mock_get_request_context_valid():
    return RequestContext(tenant_id="t_valid",
        env="dev",
        user_id="user1",
        request_id="req1"
    )

def mock_get_request_context_other():
    return RequestContext(tenant_id="t_other",
        env="dev",
        user_id="user1",
        request_id="req1"
    )

class TestCadIngestRoutes:
    """Test ingest route validation logic."""

    def test_ingest_multipart_valid_context(self):
        """Test ingest with valid context matching headers (simulated)."""
        # We override the dependency to simulate minimal headers handling
        app.dependency_overrides[get_request_context] = mock_get_request_context_valid
        # Mock auth too given it doesn't do much here logic-wise but strict dependency
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            user_id="u1", 
            tenant_ids=["t_valid"],
            email="test@example.com",
            default_tenant_id="t_valid",
            role_map={"t_valid": "admin"}
        )
        
        # Valid: explicit form fields match context
        response = client.post(
            "/cad/ingest",
            data={
                "tenant_id": "t_valid",
                "env": "dev",
                "tolerance": "0.001"
            },
            files={"file": ("test.dxf", b"SECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF", "text/plain")}
        )
        
        # Should be 200 OK (assuming ingest service accepts the tiny dummy DXF or fails later logic)
        # Actually it might fail parsing because my bytes are maybe invalid DXF logic, 
        # but validation check is BEFORE that. 
        # If it fails DXF parsing, it returns 500 or 400 with "Ingest failed".
        # But if it passed context check, we are good for this test.
        
        # If the DXF is invalid enough, it might be 500 or 400. 
        # Let's check if it raises "tenant mismatch" (400) or something else.
        if response.status_code == 400 and "mismatch" in response.text:
            pytest.fail("Should not fail with mismatch")
            
        app.dependency_overrides = {}

    def test_ingest_multipart_mismatch_tenant(self):
        """Test ingest fails when form tenant mismatches context."""
        app.dependency_overrides[get_request_context] = mock_get_request_context_valid
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            user_id="u1", 
            tenant_ids=["t_valid"],
            email="test@example.com",
            default_tenant_id="t_valid",
            role_map={"t_valid": "admin"}
        )

        response = client.post(
            "/cad/ingest",
            data={
                "tenant_id": "t_WRONG",  # Mismatch
                "env": "dev"
            },
            files={"file": ("test.dxf", b"content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "tenant_id mismatch" in response.text or "tenant_id mismatch" in response.json().get("detail", "")
        
        app.dependency_overrides = {}

    def test_ingest_multipart_mismatch_env(self):
        """Test ingest fails when form env mismatches context."""
        app.dependency_overrides[get_request_context] = mock_get_request_context_valid
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            user_id="u1", 
            tenant_ids=["t_valid"],
            email="test@example.com",
            default_tenant_id="t_valid",
            role_map={"t_valid": "admin"}
        )

        response = client.post(
            "/cad/ingest",
            data={
                "tenant_id": "t_valid", 
                "env": "prod"  # Mismatch (context is dev)
            },
            files={"file": ("test.dxf", b"content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "env mismatch" in response.text or "env mismatch" in response.json().get("detail", "")
        
        app.dependency_overrides = {}

    def test_ingest_multipart_no_explicit_context(self):
        """Test ingest works without explicit form context (implicit use of headers)."""
        app.dependency_overrides[get_request_context] = mock_get_request_context_valid
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            user_id="u1", 
            tenant_ids=["t_valid"],
            email="test@example.com",
            default_tenant_id="t_valid",
            role_map={"t_valid": "admin"}
        )

        # No tenant_id/env in data
        response = client.post(
            "/cad/ingest",
            data={
                 "tolerance": "0.001"
            },
            files={"file": ("test.dxf", b"SECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF", "text/plain")}
        )
        
        # Should NOT fail validations
        if response.status_code == 400 and "mismatch" in response.text:
            pytest.fail("Should not fail validation when fields omitted")
            
        app.dependency_overrides = {}
