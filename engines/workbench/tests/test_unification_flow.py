import pytest
from engines.common.identity import RequestContext
from engines.workbench.store import VersionedStore
from engines.workbench.models import ToolDefinition

from engines.routing.registry import set_routing_registry, InMemoryRoutingRegistry, ResourceRoute

@pytest.fixture(autouse=True)
def setup_routing():
    # 1. Setup InMemory Routing Registry
    reg = InMemoryRoutingRegistry()
    set_routing_registry(reg)
    
    # 2. Register Route for workbench_store
    route = ResourceRoute(
        id="route_1",
        resource_kind="workbench_store",
        tenant_id="t_test",
        project_id="p_test",
        env="local",
        backend_type="filesystem",
        config={}
    )
    reg.upsert_route(route)
    
    yield
    set_routing_registry(None)

@pytest.fixture
def ctx():
    return RequestContext(
        tenant_id="t_test",
        mode="lab",
        env="local",
        project_id="p_test",
        user_id="u_test",
        surface_id="s_test",
        app_id="a_test",
        request_id="req_1"
    )

def test_draft_store_lifecycle(ctx):
    store = VersionedStore()
    tool_name = "test-tool-store"
    payload = {
        "name": tool_name,
        "version": "1.0.0",
        "scopes": [
            {"scope_name": "read", "description": "Read access"},
            {"scope_name": "write", "requires_firearms": True}
        ]
    }

    # 1. Save Draft
    item = store.put_draft(ctx, tool_name, payload)
    assert item.key == tool_name
    assert item.version == "draft"
    assert item.data["name"] == tool_name

    # 2. Get Draft
    loaded = store.get_draft(ctx, tool_name)
    assert loaded is not None
    assert loaded.data["name"] == tool_name
    assert len(loaded.data["scopes"]) == 2

    # 3. List All Drafts
    drafts = store.list_all_drafts(ctx)
    assert len(drafts) >= 1
    found = next((d for d in drafts if d.key == tool_name), None)
    assert found is not None
    assert found.version == "draft"
    
    # 4. Publish (Simulated Commit)
    published = store.publish(ctx, tool_name, "1.0.0")
    assert published.version == "1.0.0"
    
    # 5. Verify published version exists
    v = store.get_version(ctx, tool_name, "1.0.0")
    assert v is not None
    assert v.version == "1.0.0"
