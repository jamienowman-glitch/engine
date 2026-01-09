import pytest
import shutil
import os
from engines.nexus.blob_store import NexusBlobStore
from engines.nexus.schemas import SpaceKey, Scope

@pytest.fixture
def blob_store():
    root = "/tmp/nexus_test_media"
    if os.path.exists(root):
        shutil.rmtree(root)
    return NexusBlobStore(protocol="file", root_path=root)

def test_blob_lifecycle(blob_store):
    """Test put, get, exists, resolve."""
    key = SpaceKey(
        scope=Scope.TENANT,
        tenant_id="t_media",
        env="dev",
        project_id="p1",
        surface_id="s1",
        space_id="main"
    )
    blob_id = "image_123.jpg"
    data = b"fake_image_bytes"

    # 1. Put
    uri = blob_store.put_bytes(key, blob_id, data)
    assert uri.endswith(blob_id)
    assert "t_media" in uri

    # 2. Exists
    assert blob_store.exists(key, blob_id)
    assert not blob_store.exists(key, "missing.jpg")

    # 3. Get
    read_data = blob_store.get_bytes(key, blob_id)
    assert read_data == data

def test_blob_isolation(blob_store):
    """Ensure blobs are isolated by tenant/path."""
    key_a = SpaceKey(
        scope=Scope.TENANT,
        tenant_id="t_A",
        env="dev",
        project_id="p1",
        surface_id="s1",
        space_id="main"
    )
    key_b = SpaceKey(
        scope=Scope.TENANT,
        tenant_id="t_B",
        env="dev",
        project_id="p1",
        surface_id="s1",
        space_id="main"
    )

    blob_store.put_bytes(key_a, "test.txt", b"A data")

    # B should not find it
    assert not blob_store.exists(key_b, "test.txt")

    # B writes same name
    blob_store.put_bytes(key_b, "test.txt", b"B data")

    # Verify content distinct
    assert blob_store.get_bytes(key_a, "test.txt") == b"A data"
    assert blob_store.get_bytes(key_b, "test.txt") == b"B data"
