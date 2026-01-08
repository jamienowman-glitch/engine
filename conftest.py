import sys
from pathlib import Path
import os
from uuid import uuid4
from engines.routing.registry import InMemoryRoutingRegistry, set_routing_registry, ResourceRoute
from engines.routing import manager as routing_manager
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store

# Ensure repo root on sys.path for imports from anywhere in tests tree.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("BUDGET_BACKEND", "filesystem")
os.environ.setdefault("BUDGET_BACKEND_FS_DIR", "/tmp/budget-test")
os.environ.setdefault("FEATURE_FLAGS_BACKEND", "memory")
os.environ.setdefault("GCP_PROJECT", "test-project")
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8080")

# Setup Registry
registry = InMemoryRoutingRegistry()
set_routing_registry(registry)

# Seed event_stream route for tests (maps to firestore but we override the store anyway)
registry.upsert_route(ResourceRoute(
    id=str(uuid4()),
    resource_kind="event_stream",
    tenant_id="t_system",
    env="dev",
    backend_type="firestore"
))

routing_manager.startup_validation_check = lambda: None
set_identity_repo(InMemoryIdentityRepository())

# Override Timeline Store with InMemory for all tests
set_timeline_store(InMemoryTimelineStore())
