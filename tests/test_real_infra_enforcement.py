import pytest
import os
import sys
import importlib
from unittest import mock

# Clear environment variables to simulate "missing config" state
@pytest.fixture
def clean_env():
    # We must clear these to ensure we trigger the failure paths
    keys_to_remove = [
        "RAW_BUCKET", "IDENTITY_BACKEND", 
        "CHAT_BUS_BACKEND", "NEXUS_BACKEND",
        "REDIS_HOST", "REDIS_PORT"
    ]
    old_environ = {}
    for k in keys_to_remove:
        if k in os.environ:
            old_environ[k] = os.environ[k]
            del os.environ[k]
            
    yield
    
    # Restore
    os.environ.update(old_environ)

def test_media_service_fails_fast_without_config(clean_env):
    """MediaService should fail if S3 bucket is not configured."""
    from engines.media_v2 import service
    importlib.reload(service)
    from engines.media_v2.service import S3MediaStorage
    
    with pytest.raises(RuntimeError, match="RAW_BUCKET config missing"):
        S3MediaStorage()

def test_identity_fails_fast(clean_env):
    """Identity default repo should fail on access if backend not set."""
    from engines.identity import state
    importlib.reload(state)
    
    # Import succeeds now (lazy)
    repo = state.identity_repo
    
    # Access triggers crash
    with pytest.raises(RuntimeError, match="IDENTITY_BACKEND must be 'firestore'"):
        getattr(repo, "get_user")

def test_chat_fails_fast(clean_env):
    """Chat bus should fail on access if backend not set."""
    from engines.chat.service import transport_layer
    importlib.reload(transport_layer)
    
    bus = transport_layer.bus
    
    with pytest.raises(RuntimeError, match="CHAT_BUS_BACKEND must be 'redis'"):
        getattr(bus, "list_threads")

def test_nexus_fails_fast_on_memory(clean_env):
    """Nexus should fail if backend is explicitly memory."""
    from engines.nexus import backends
    
    with mock.patch.dict(os.environ, {"NEXUS_BACKEND": "memory"}):
        with pytest.raises(RuntimeError, match="not allowed in Real Infra mode"):
            importlib.reload(backends)
            backends.get_backend()

def test_nexus_fails_unknown(clean_env):
    """Nexus should fail if backend is unknown."""
    from engines.nexus import backends
    
    with mock.patch.dict(os.environ, {"NEXUS_BACKEND": "alien_tech"}):
        with pytest.raises(RuntimeError, match="unsupported NEXUS_BACKEND"):
             importlib.reload(backends)
             backends.get_backend()

