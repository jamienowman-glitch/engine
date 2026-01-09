import pytest
from engines.common.identity import RequestContext
from engines.run_memory.service import RunMemoryService
from engines.run_memory.cloud_run_memory import VersionConflictError, FirestoreRunMemory, DynamoDBRunMemory, CosmosRunMemory

# Mock classes to avoid real cloud connections
class MockFirestoreRunMemory(FirestoreRunMemory):
    def __init__(self, project=None):
        self._store = {}

    def write(self, key, value, context, run_id, expected_version=None):
        doc_id = f"{context.tenant_id}#{context.mode}#{context.project_id}#{run_id}#{key}"
        current = self._store.get(doc_id, {"version": 0})

        if expected_version is not None and expected_version != current["version"]:
            raise VersionConflictError("Version conflict")

        new_version = current["version"] + 1
        self._store[doc_id] = {
            "key": key,
            "value": value,
            "version": new_version,
            "created_by": context.user_id,
            "updated_by": context.user_id,
        }
        return self._store[doc_id]

    def read(self, key, context, run_id, version=None):
        doc_id = f"{context.tenant_id}#{context.mode}#{context.project_id}#{run_id}#{key}"
        data = self._store.get(doc_id)
        if not data:
            return None
        if version is not None and data["version"] != version:
            return None
        return data

    def list_keys(self, context, run_id):
        keys = []
        for k, v in self._store.items():
            if run_id in k: # weak check but okay for mock
                 keys.append(v["key"])
        return keys

# Mock routing registry
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_registry():
    with patch("engines.run_memory.service.routing_registry") as mock:
        yield mock

@pytest.fixture
def context():
    return RequestContext(
        tenant_id="t_tenant1",
        mode="saas",
        project_id="project-1",
        user_id="user-1"
    )

def test_run_memory_service_resolve(mock_registry, context):
    mock_registry.return_value.get_route.return_value = MagicMock(
        backend_type="firestore",
        config={"project": "test-project"}
    )

    # We mock FirestoreRunMemory to avoid google.cloud dependency failure
    with patch("engines.run_memory.service.FirestoreRunMemory", MockFirestoreRunMemory):
        service = RunMemoryService(context)
        assert isinstance(service._adapter, MockFirestoreRunMemory)

def test_run_memory_write_read(mock_registry, context):
    mock_registry.return_value.get_route.return_value = MagicMock(
        backend_type="firestore",
        config={"project": "test-project"}
    )

    with patch("engines.run_memory.service.FirestoreRunMemory", MockFirestoreRunMemory):
        service = RunMemoryService(context)

        # Write
        result = service.write(key="test-key", value="test-value", run_id="run-1")
        assert result["key"] == "test-key"
        assert result["value"] == "test-value"
        assert result["version"] == 1

        # Read
        read_result = service.read(key="test-key", run_id="run-1")
        assert read_result["value"] == "test-value"
        assert read_result["version"] == 1

        # Optimistic Concurrency
        try:
            service.write(key="test-key", value="val2", run_id="run-1", expected_version=0)
            assert False, "Should raise VersionConflictError"
        except VersionConflictError:
            pass

        # Success write with correct version
        result2 = service.write(key="test-key", value="val2", run_id="run-1", expected_version=1)
        assert result2["version"] == 2

def test_run_memory_backward_compatibility(mock_registry, context):
    # Simulate missing run_memory but existing blackboard_store
    def side_effect(resource_kind, **kwargs):
        if resource_kind == "run_memory":
            return None
        if resource_kind == "blackboard_store":
            return MagicMock(backend_type="firestore", config={"project": "test-project"})
        return None

    mock_registry.return_value.get_route.side_effect = side_effect

    with patch("engines.run_memory.service.FirestoreRunMemory", MockFirestoreRunMemory):
        service = RunMemoryService(context)
        assert isinstance(service._adapter, MockFirestoreRunMemory)
