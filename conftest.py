import sys
from pathlib import Path
import os
from engines.routing.registry import InMemoryRoutingRegistry, set_routing_registry
from engines.routing import manager as routing_manager
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo

# Ensure repo root on sys.path for imports from anywhere in tests tree.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("BUDGET_BACKEND", "filesystem")
os.environ.setdefault("BUDGET_BACKEND_FS_DIR", "/tmp/budget-test")
os.environ.setdefault("FEATURE_FLAGS_BACKEND", "firestore")
os.environ.setdefault("GCP_PROJECT", "test-project")
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8080")
set_routing_registry(InMemoryRoutingRegistry())
routing_manager.startup_validation_check = lambda: None
set_identity_repo(InMemoryIdentityRepository())
