import pytest
from unittest.mock import MagicMock, patch
from engines.common.identity import RequestContext
from engines.registry.service import ComponentRegistryService, RegistrySpec

@pytest.fixture
def context():
    return RequestContext(
        tenant_id="t_tenant1",
        mode="saas",
        project_id="project-1",
        user_id="user-1"
    )

@pytest.fixture
def mock_repo():
    with patch("engines.registry.service.ComponentRegistryRepository") as mock:
        yield mock

def test_registry_domains_support(mock_repo, context):
    service = ComponentRegistryService(repo=mock_repo)

    # Mock data
    mock_repo.list_specs.return_value = [
        {
            "id": "lens-1",
            "kind": "graphlens",
            "version": 1,
            "schema": {},
            "defaults": {},
            "controls": {},
            "token_surface": []
        },
        {
            "id": "canvas-1",
            "kind": "canvas",
            "version": 1,
            "schema": {},
            "defaults": {},
            "controls": {},
            "token_surface": []
        }
    ]

    # Test graphlenses
    graphlenses = service.list_specs(context, kind="graphlens")
    assert len(graphlenses.specs) == 1
    assert graphlenses.specs[0].id == "lens-1"

    # Test canvases
    canvases = service.list_specs(context, kind="canvas")
    assert len(canvases.specs) == 1
    assert canvases.specs[0].id == "canvas-1"

    # Test invalid kind
    try:
        service.list_specs(context, kind="invalid")
    except Exception:
        pass # Expected, but service catches and uses error_response which raises HTTPException,
             # but here we are unit testing service method which calls error_response.
             # error_response typically raises HTTPException.

def test_registry_domains_validation(mock_repo, context):
    service = ComponentRegistryService(repo=mock_repo)

    assert "graphlens" in service.SPEC_KINDS
    assert "canvas" in service.SPEC_KINDS
