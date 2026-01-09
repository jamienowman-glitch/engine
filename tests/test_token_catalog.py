"""Tests for Token Catalog (EN-04)."""
import pytest
from unittest.mock import MagicMock, patch
from engines.common.identity import RequestContext
from engines.canvas_reducer import CanvasState, NodeState, EdgeState, TokenState
from engines.canvas_reducer.router import get_token_catalog, CanvasService

@pytest.fixture
def context():
    return RequestContext(
        tenant_id="t_tenant1",
        mode="saas",
        project_id="project-1",
        user_id="user-1"
    )

@pytest.fixture
def auth():
    auth_mock = MagicMock()
    auth_mock.check_tenant_access.return_value = True
    return auth_mock

def test_token_catalog_structure(context, auth):
    # Mock service
    service = MagicMock(spec=CanvasService)

    # Mock state
    state = CanvasState()
    state.nodes["n1"] = NodeState(id="n1", type="process", data={"label": "A"})
    state.edges["e1"] = EdgeState(id="e1", source="n1", target="n2")
    state.tokens["t1"] = TokenState(id="t1", node_id="n1", value=123)

    service.get_snapshot.return_value = state
    service.get_head_rev.return_value = 5

    # Call endpoint function directly (bypass FastAPI routing logic, verify logic)
    # We need to mock require_tenant_membership if it wasn't mocked.
    # But here we just call the function.

    # Mock require_tenant_membership in engines.canvas_reducer.router
    with patch("engines.canvas_reducer.router.require_tenant_membership"):
        payload = get_token_catalog(
            canvas_id="canvas-1",
            context=context,
            auth=auth,
            service=service
        )

    assert payload.canvas_id == "canvas-1"
    assert payload.head_rev == 5

    # Check elements
    assert len(payload.elements) == 2
    n1 = next(e for e in payload.elements if e["id"] == "n1")
    assert n1["category"] == "node"
    assert n1["type"] == "process"

    e1 = next(e for e in payload.elements if e["id"] == "e1")
    assert e1["category"] == "edge"

    # Check values
    assert payload.values["t1"] == 123

    # Check schemas
    assert payload.schemas == {}
