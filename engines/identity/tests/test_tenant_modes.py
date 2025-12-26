"""Tests for tenant mode CRUD and seeding."""
import os
import pytest
from unittest.mock import patch

from engines.identity.models import TenantMode
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo


@pytest.fixture(autouse=True)
def reset_repo():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    return repo


def test_create_tenant_mode():
    """Test creating a tenant mode."""
    from engines.identity.state import identity_repo
    
    mode = TenantMode(name="enterprise", description="Enterprise deployment mode")
    created = identity_repo.create_tenant_mode(mode)
    
    assert created.id == mode.id
    assert created.name == "enterprise"
    assert created.description == "Enterprise deployment mode"


def test_get_tenant_mode_by_id():
    """Test retrieving a tenant mode by ID."""
    from engines.identity.state import identity_repo
    
    mode = TenantMode(name="saas", description="SaaS deployment mode")
    created = identity_repo.create_tenant_mode(mode)
    
    retrieved = identity_repo.get_tenant_mode(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == "saas"


def test_get_tenant_mode_by_name():
    """Test retrieving a tenant mode by name."""
    from engines.identity.state import identity_repo
    
    mode = TenantMode(name="lab", description="Lab deployment mode")
    identity_repo.create_tenant_mode(mode)
    
    retrieved = identity_repo.get_tenant_mode_by_name("lab")
    assert retrieved is not None
    assert retrieved.name == "lab"
    assert retrieved.description == "Lab deployment mode"


def test_get_tenant_mode_by_name_not_found():
    """Test retrieving a nonexistent tenant mode by name."""
    from engines.identity.state import identity_repo
    
    retrieved = identity_repo.get_tenant_mode_by_name("nonexistent")
    assert retrieved is None


def test_list_tenant_modes():
    """Test listing all tenant modes."""
    from engines.identity.state import identity_repo
    
    mode1 = TenantMode(name="enterprise", description="Enterprise")
    mode2 = TenantMode(name="saas", description="SaaS")
    mode3 = TenantMode(name="lab", description="Lab")
    
    identity_repo.create_tenant_mode(mode1)
    identity_repo.create_tenant_mode(mode2)
    identity_repo.create_tenant_mode(mode3)
    
    modes = identity_repo.list_tenant_modes()
    assert len(modes) == 3
    mode_names = {m.name for m in modes}
    assert mode_names == {"enterprise", "saas", "lab"}


def test_list_tenant_modes_empty():
    """Test listing modes when none exist."""
    from engines.identity.state import identity_repo
    
    modes = identity_repo.list_tenant_modes()
    assert modes == []


def test_bootstrap_seeds_modes():
    """Test that bootstrap_tenants idempotently seeds tenant modes."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from engines.identity.routes_auth import router
    from engines.identity.state import identity_repo
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    with patch.dict(os.environ, {"SYSTEM_BOOTSTRAP_KEY": "secret-123"}):
        response = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "secret-123"}
        )
        assert response.status_code == 200
        
        # Verify modes are created
        modes = identity_repo.list_tenant_modes()
        assert len(modes) == 3
        mode_names = {m.name for m in modes}
        assert mode_names == {"enterprise", "saas", "lab"}


def test_bootstrap_seeds_modes_idempotent():
    """Test that bootstrap_tenants idempotently handles mode seeding."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from engines.identity.routes_auth import router
    from engines.identity.state import identity_repo
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    with patch.dict(os.environ, {"SYSTEM_BOOTSTRAP_KEY": "secret-123"}):
        # First bootstrap
        response1 = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "secret-123"}
        )
        assert response1.status_code == 200
        modes_after_first = identity_repo.list_tenant_modes()
        assert len(modes_after_first) == 3
        
        # Second bootstrap (idempotent)
        response2 = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "secret-123"}
        )
        assert response2.status_code == 200
        modes_after_second = identity_repo.list_tenant_modes()
        assert len(modes_after_second) == 3  # Still 3, not 6


def test_tenant_mode_metadata():
    """Test that tenant mode metadata dict is preserved."""
    from engines.identity.state import identity_repo
    
    metadata = {"custom_field": "custom_value"}
    mode = TenantMode(name="custom", description="Custom mode", metadata=metadata)
    created = identity_repo.create_tenant_mode(mode)
    
    retrieved = identity_repo.get_tenant_mode(created.id)
    assert retrieved.metadata == metadata
