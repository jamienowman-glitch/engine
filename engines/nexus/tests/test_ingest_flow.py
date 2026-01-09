import pytest
import asyncio
from engines.nexus.worker import NexusWorker
from engines.nexus.signals import IngestRequest
from engines.nexus.lance_store import LanceVectorStore
from engines.nexus.blob_store import NexusBlobStore
from engines.nexus.schemas import SpaceKey, Scope

@pytest.fixture
def worker():
    store = LanceVectorStore(root_uri="/tmp/nexus_worker_test")
    blob = NexusBlobStore(root_path="/tmp/nexus_worker_media")
    return NexusWorker(store, blob)

@pytest.mark.asyncio
async def test_ingest_flow(worker):
    """Test that event processing leads to data in store."""

    # 1. Create Event
    event = IngestRequest(
        space_id="worker_space",
        tenant_id="t_worker",
        items=[
            {"id": "doc1", "text": "hello worker", "kind": "data"}
        ],
        trace_id="task_1"
    )

    # 2. Process Event
    await worker.handle_ingest_event(event)

    # 3. Verify Store
    key = SpaceKey(
        scope=Scope.TENANT,
        tenant_id="t_worker",
        env="dev",
        project_id="default",
        surface_id="default",
        space_id="worker_space"
    )

    # Query to check existence
    result = worker.vector_store.query(key, [0.1]*768, top_k=1)
    assert len(result.hits) == 1
    assert result.hits[0].id == "doc1"
