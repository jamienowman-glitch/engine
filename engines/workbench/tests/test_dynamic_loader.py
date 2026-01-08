import os
import shutil
import pytest
from unittest.mock import patch, MagicMock
from engines.mcp_gateway.inventory import get_inventory
from engines.workbench.dynamic_loader import loader, LoaderService

# Define paths for test isolation
TEST_CONNECTORS_DIR = "engines/connectors/test_conn"
TEST_MUSCLE_DIR = "engines/muscles/test_muscle/mcp"

@pytest.fixture
def clean_inventory():
    inv = get_inventory()
    inv._tools = {}
    return inv

def test_loader_empty_default(clean_inventory):
    # Ensure no non-template tools exist locally for this test context
    # If dev env has folders, we might need to mock os.listdir or use a temp root
    # But for "empty by default" rule, checking that currently no tools are loaded is good.
    loader.load_all()
    tools = clean_inventory.list_tools()
    # Should be empty because only _template exists and loader ignores it
    assert len(tools) == 0

def test_loader_populates_connector(clean_inventory):
    # Create valid connector structure
    os.makedirs(TEST_CONNECTORS_DIR, exist_ok=True)
    
    with open(f"{TEST_CONNECTORS_DIR}/spec.yaml", "w") as f:
        f.write('id: "test_tool"\nname: "Test Tool"\nscopes:\n  - name: "run"\n    handler: "handle_run"\n    input_model: "RunInput"\n')
        
    with open(f"{TEST_CONNECTORS_DIR}/impl.py", "w") as f:
        f.write('from pydantic import BaseModel\nclass RunInput(BaseModel):\n  x: int\nasync def handle_run(ctx, args): return "ok"')

    try:
        # Must enable "test_conn" (directory name)
        with patch.dict(os.environ, {"ENABLED_CONNECTORS": "test_conn"}):
            loader.load_all()
        
        tools = clean_inventory.list_tools()
        assert len(tools) == 1
        assert tools[0].id == "test_tool"
        assert "run" in tools[0].scopes
    finally:
        shutil.rmtree(TEST_CONNECTORS_DIR, ignore_errors=True)

def test_loader_populates_muscle(clean_inventory):
    # Create valid muscle structure
    os.makedirs(TEST_MUSCLE_DIR, exist_ok=True)
    
    with open(f"{TEST_MUSCLE_DIR}/spec.yaml", "w") as f:
        f.write('id: "test_muscle"\nname: "Test Muscle"\nscopes:\n  - name: "flex"\n    handler: "handle_flex"\n    input_model: "FlexInput"\n')
        
    with open(f"{TEST_MUSCLE_DIR}/impl.py", "w") as f:
        f.write('from pydantic import BaseModel\nclass FlexInput(BaseModel):\n  power: int\nasync def handle_flex(ctx, args): return "strong"')

    try:
        # Must enable "test_muscle" (directory name)
        with patch.dict(os.environ, {"ENABLED_MUSCLES": "test_muscle"}):
            loader.load_all()
        
        assert get_inventory().get_tool("test_muscle") is not None
    finally:
        shutil.rmtree("engines/muscles/test_muscle", ignore_errors=True)
