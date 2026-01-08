import os
import shutil
import pytest
from engines.workbench.dynamic_loader import loader, ENGINES_DIR
from engines.mcp_gateway.inventory import get_inventory

from unittest.mock import patch

# Must not start with _ or . to be scanned
TEST_CONN_DIR = os.path.join(ENGINES_DIR, "connectors", "test_reload_conn")

@pytest.fixture
def clean_test_connector():
    # Setup
    if os.path.exists(TEST_CONN_DIR):
        shutil.rmtree(TEST_CONN_DIR)
    os.makedirs(TEST_CONN_DIR)
    
    yield TEST_CONN_DIR
    
    # Teardown
    if os.path.exists(TEST_CONN_DIR):
        shutil.rmtree(TEST_CONN_DIR)

def test_reload_picks_up_new_connector(clean_test_connector):
    """Verify that reload() finds new files on disk."""
    
    # Patch Environment to whitelist this test connector
    # We need to include existing enabled ones? Or just this one.
    with patch.dict(os.environ, {"ENABLED_CONNECTORS": "test_reload_conn"}):
        
        # 1. Initial State
        loader.reload() # Start fresh with our env var active
        initial_tools = get_inventory().list_tools()
        initial_ids = {t.id for t in initial_tools}
        
        assert "conn.test.dynamic" not in initial_ids
        
        # 2. Write New Connector
        with open(os.path.join(TEST_CONN_DIR, "spec.yaml"), "w") as f:
            f.write("""
id: conn.test.dynamic
name: Dynamic Test Tool
scopes: []
""")
        
        with open(os.path.join(TEST_CONN_DIR, "impl.py"), "w") as f:
            f.write("# Empty impl")

        # 3. Reload
        loader.reload()
        
        # 4. Verify
        new_tools = get_inventory().list_tools()
        new_ids = {t.id for t in new_tools}
        
        assert "conn.test.dynamic" in new_ids
        assert len(new_tools) == len(initial_tools) + 1

def test_clear_resets_inventory():
    """Verify clear() empties the inventory."""
    # Ensure something is loaded
    loader.reload()
    if not get_inventory().list_tools():
        # If empty, we can't really test clear decremented count, but we can test it stays 0
        pass
        
    get_inventory().clear()
    assert len(get_inventory().list_tools()) == 0
