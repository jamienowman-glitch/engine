import pytest
from fastapi import HTTPException
from engines.nexus.service import NexusService
from engines.nexus.schemas import SpaceKey, Scope, NexusIngestRequest, NexusKind
from engines.nexus.lance_store import LanceVectorStore

@pytest.fixture
def service():
    store = LanceVectorStore()
    return NexusService(store=store)

@pytest.mark.asyncio
async def test_global_write_permission_denied(service):
    """Test that normal tenant cannot write to GLOBAL scope."""

    key = SpaceKey(
        scope=Scope.GLOBAL,
        tenant_id="t_user", # Normal user trying to write global
        env="dev",
        project_id="p1",
        surface_id="s1",
        space_id="main"
    )

    req = NexusIngestRequest(
        tenantId="t_user",
        env="dev",
        kind=NexusKind.data,
        docs=[]
    )

    with pytest.raises(HTTPException) as exc:
        await service.ingest(key, req)

    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == "nexus.permission_denied"

@pytest.mark.asyncio
async def test_global_write_permission_allowed(service):
    """Test that system tenant CAN write to GLOBAL scope."""

    key = SpaceKey(
        scope=Scope.GLOBAL,
        tenant_id="t_system", # System user
        env="dev",
        project_id="p1",
        surface_id="s1",
        space_id="main"
    )

    req = NexusIngestRequest(
        tenantId="t_system",
        env="dev",
        kind=NexusKind.data,
        docs=[]
    )

    # Should not raise
    await service.ingest(key, req)
