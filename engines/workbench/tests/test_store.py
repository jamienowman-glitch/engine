import pytest
from engines.workbench.store import VersionedStore

def test_versioned_store_lifecycle():
    store = VersionedStore[dict]()
    key = "pkg.my-tool"
    
    # 1. Create Draft
    data = {"name": "My Tool", "foo": "bar"}
    store.put_draft(key, data)
    
    draft = store.get_draft(key)
    assert draft is not None
    assert draft.data["foo"] == "bar"
    assert draft.version == "draft"
    
    # 2. Update Draft
    data_v2 = {"name": "My Tool", "foo": "baz"}
    store.put_draft(key, data_v2)
    draft_v2 = store.get_draft(key)
    assert draft_v2.data["foo"] == "baz"
    
    # 3. Publish
    published = store.publish(key, "1.0.0")
    assert published.version == "1.0.0"
    assert published.data["foo"] == "baz"
    
    # 4. Verify immutability (conceptually, store holds separate item)
    # Get version back
    v1 = store.get_version(key, "1.0.0")
    assert v1 is not None
    assert v1.data["foo"] == "baz"
    
    # 5. Draft still exists (or should it be cleared? Decision: Published artifact is snapshot. Draft persists for next iter.)
    # In this impl, draft persists.
    draft_after = store.get_draft(key)
    assert draft_after is not None
    
    # 6. Publish duplicate fails
    with pytest.raises(ValueError):
        store.publish(key, "1.0.0")

def test_publish_no_draft_fails():
    store = VersionedStore[dict]()
    with pytest.raises(ValueError):
        store.publish("missing", "1.0.0")
