import pytest
from engines.nexus.signals import IngestRequest
from engines.routing.resource_kinds import NEXUS_STORE, NEXUS_BLOB_STORE, ResourceKind

def test_ingest_request_model():
    """Test that IngestRequest can be instantiated."""
    req = IngestRequest(
        space_id="test-space",
        tenant_id="t_test",
        items=[{"type": "text", "content": "hello"}]
    )
    assert req.space_id == "test-space"
    assert req.tenant_id == "t_test"
    assert len(req.items) == 1

def test_resource_kinds_exist():
    """Test that new resource kinds are defined and accessible."""
    assert NEXUS_STORE == "nexus_store"
    assert NEXUS_BLOB_STORE == "nexus_blob_store"
    assert ResourceKind.NEXUS_STORE == "nexus_store"
    assert ResourceKind.NEXUS_BLOB_STORE == "nexus_blob_store"
