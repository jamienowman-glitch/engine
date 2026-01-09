import pytest
import shutil
import os
from engines.nexus.lance_store import LanceVectorStore
from engines.nexus.schemas import SpaceKey, Scope, NexusEmbedding, NexusKind

@pytest.fixture
def store():
    root = "/tmp/nexus_test_data"
    if os.path.exists(root):
        shutil.rmtree(root)
    return LanceVectorStore(root_uri=root)

def test_tenant_isolation(store):
    """Verify that Tenant A cannot see Tenant B's data."""

    # 1. Setup Keys
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

    # 2. Insert Data
    vec_a = NexusEmbedding(
        doc_id="doc_a",
        tenant_id="t_A",
        env="dev",
        kind=NexusKind.data,
        embedding=[0.1] * 768,
        model_id="test",
        metadata={"text": "I am A"}
    )
    vec_b = NexusEmbedding(
        doc_id="doc_b",
        tenant_id="t_B",
        env="dev",
        kind=NexusKind.data,
        embedding=[0.2] * 768,
        model_id="test",
        metadata={"text": "I am B"}
    )

    store.upsert(key_a, [vec_a])
    store.upsert(key_b, [vec_b])

    # 3. Query A
    res_a = store.query(key_a, [0.1] * 768, top_k=10)
    ids_a = [h.id for h in res_a.hits]

    assert "doc_a" in ids_a
    assert "doc_b" not in ids_a

    # 4. Query B
    res_b = store.query(key_b, [0.2] * 768, top_k=10)
    ids_b = [h.id for h in res_b.hits]

    assert "doc_b" in ids_b
    assert "doc_a" not in ids_b

def test_global_fusion(store):
    """Verify include_global=True merges results."""

    # Tenant Key
    key_t = SpaceKey(
        scope=Scope.TENANT,
        tenant_id="t_user",
        env="dev",
        project_id="p1",
        surface_id="marketing",
        space_id="main"
    )
    # Global Key (t_system, same surface)
    key_g = SpaceKey(
        scope=Scope.GLOBAL,
        tenant_id="t_system",
        env="dev",
        project_id="p1",
        surface_id="marketing",
        space_id="main"
    )

    # Insert Global Data
    vec_g = NexusEmbedding(
        doc_id="doc_global",
        tenant_id="t_system",
        env="dev",
        kind=NexusKind.data,
        embedding=[0.9] * 768,
        model_id="test",
        metadata={"text": "Global Knowledge"}
    )
    store.upsert(key_g, [vec_g])

    # Insert Tenant Data
    vec_t = NexusEmbedding(
        doc_id="doc_tenant",
        tenant_id="t_user",
        env="dev",
        kind=NexusKind.data,
        embedding=[0.9] * 768,
        model_id="test",
        metadata={"text": "User Knowledge"}
    )
    store.upsert(key_t, [vec_t])

    # Query without global
    res_1 = store.query(key_t, [0.9] * 768, top_k=10, include_global=False)
    ids_1 = [h.id for h in res_1.hits]
    assert "doc_tenant" in ids_1
    assert "doc_global" not in ids_1

    # Query with global
    res_2 = store.query(key_t, [0.9] * 768, top_k=10, include_global=True)
    ids_2 = [h.id for h in res_2.hits]
    assert "doc_tenant" in ids_2
    assert "doc_global" in ids_2

    # Check source scope
    for h in res_2.hits:
        if h.id == "doc_global":
            assert h.metadata["source_scope"] == "global"
        if h.id == "doc_tenant":
            assert h.metadata["source_scope"] == "tenant"
