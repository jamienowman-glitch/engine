from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from engines.common.identity import RequestContext, get_request_context
from engines.identity.models import Surface, App
from engines.identity.repository import InMemoryIdentityRepository

# Use in-memory repo for tests
test_repo = InMemoryIdentityRepository()

app = FastAPI()


@app.api_route("/context", methods=["GET", "POST"])
def _context_sample(context: RequestContext = Depends(get_request_context)) -> dict[str, str]:
    return {
        "tenant_id": context.tenant_id,
        "env": context.env,
        "project_id": context.project_id,
        "surface_id": context.surface_id,
        "app_id": context.app_id,
        "request_id": context.request_id,
    }


client = TestClient(app)
BASE_HEADERS = {
    "X-Tenant-Id": "t_test",
    "X-Env": "dev",
    "X-Project-Id": "p_required",
}


def test_missing_project_id_errors_400() -> None:
    with patch("engines.identity.state.identity_repo", test_repo):
        headers = {k: v for k, v in BASE_HEADERS.items() if k != "X-Project-Id"}
        response = client.get("/context", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "project_id is required"


def test_project_header_allowed() -> None:
    # Setup: create default surface/app
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_test",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_test",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    with patch("engines.identity.state.identity_repo", test_repo):
        response = client.get("/context", headers=BASE_HEADERS)
        assert response.status_code == 200
        assert response.json()["project_id"] == "p_required"


def test_project_query_fallback() -> None:
    # Setup: create defaults
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_test",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_test",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    with patch("engines.identity.state.identity_repo", test_repo):
        headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
        response = client.get("/context", headers=headers, params={"project_id": "project-query"})
        assert response.status_code == 200
        assert response.json()["project_id"] == "project-query"


def test_project_body_fallback() -> None:
    # Setup: create defaults
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_body",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_body",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    with patch("engines.identity.state.identity_repo", test_repo):
        response = client.post(
            "/context",
            json={"tenant_id": "t_body", "env": "dev", "project_id": "project-body"},
        )
        assert response.status_code == 200
        assert response.json()["project_id"] == "project-body"


def test_project_required() -> None:
    """Gate 5: Validate that project_id is mandatory for all requests."""
    # Setup defaults
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_test",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_test",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    with patch("engines.identity.state.identity_repo", test_repo):
        # Test 1: Missing project_id must error 400
        headers_no_project = {
            "X-Tenant-Id": "t_test",
            "X-Env": "dev",
        }
        response = client.get("/context", headers=headers_no_project)
        assert response.status_code == 400
        assert "project_id" in response.json()["detail"]

        # Test 2: Valid project_id must succeed
        headers_with_project = {
            "X-Tenant-Id": "t_test",
            "X-Env": "dev",
            "X-Project-Id": "p_valid",
        }
        response = client.get("/context", headers=headers_with_project)
        assert response.status_code == 200
        assert response.json()["project_id"] == "p_valid"


# Phase 0 closeout: Tests for surface_id, app_id, request_id

def test_request_id_generated_if_missing() -> None:
    """Missing X-Request-Id should generate a UUID."""
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_test",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_test",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    with patch("engines.identity.state.identity_repo", test_repo):
        response = client.get("/context", headers=BASE_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"]
        assert len(data["request_id"]) == 32  # UUID hex length


def test_request_id_explicit_header() -> None:
    """Explicit X-Request-Id should be used."""
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_test",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_test",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    with patch("engines.identity.state.identity_repo", test_repo):
        headers = {**BASE_HEADERS, "X-Request-Id": "custom-req-123"}
        response = client.get("/context", headers=headers)
        assert response.status_code == 200
        assert response.json()["request_id"] == "custom-req-123"


def test_surface_app_missing_no_defaults_errors_400() -> None:
    """Missing surface/app and no defaults exist should error 400."""
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    
    with patch("engines.identity.state.identity_repo", test_repo):
        response = client.get("/context", headers=BASE_HEADERS)
        assert response.status_code == 400
        assert "surface_id" in response.json()["detail"].lower() or "default" in response.json()["detail"].lower()


def test_surface_app_defaults_used_if_exist() -> None:
    """If surface/app defaults exist, they should be used."""
    # Setup: create default surface/app for t_test
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_test",
        name="default",
        description="Test default surface",
    )
    created_surface = test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_test",
        name="default",
        app_type="web",
        description="Test default app",
    )
    created_app = test_repo.create_app(default_app)
    
    # Request without explicit surface/app should use defaults
    with patch("engines.identity.state.identity_repo", test_repo):
        response = client.get("/context", headers=BASE_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["surface_id"] == created_surface.id
        assert data["app_id"] == created_app.id


def test_surface_app_explicit_headers() -> None:
    """Explicit surface/app headers should override defaults."""
    # Setup: ensure defaults exist
    test_repo._surfaces.clear()
    test_repo._apps.clear()
    default_surface = Surface(
        tenant_id="t_explicit",
        name="default",
        description="Test default surface",
    )
    test_repo.create_surface(default_surface)
    
    default_app = App(
        tenant_id="t_explicit",
        name="default",
        app_type="web",
        description="Test default app",
    )
    test_repo.create_app(default_app)
    
    # Request with explicit surface/app
    with patch("engines.identity.state.identity_repo", test_repo):
        headers = {
            "X-Tenant-Id": "t_explicit",
            "X-Env": "dev",
            "X-Project-Id": "p_test",
            "X-Surface-Id": "s_custom",
            "X-App-Id": "a_custom",
        }
        response = client.get("/context", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["surface_id"] == "s_custom"
        assert data["app_id"] == "a_custom"
