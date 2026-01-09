import pytest
from unittest.mock import AsyncMock, patch
from engines.common.identity import RequestContext
from engines.workbench.dynamic_loader import loader
from engines.mcp_gateway.inventory import get_inventory
from engines.connectors.shopify_dev.impl import SearchDocsInput

# Reset inventory for test
import asyncio
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def reset_inventory():
    with patch.dict(os.environ, {"ENABLED_CONNECTORS": "shopify_dev"}):
        loader.reload()
        yield
        get_inventory().clear()

def test_shopify_connector_loading():
    async def _test():
        # 1. Verify connector loaded
        inv = get_inventory()
        tool = inv.get_tool("shopify-dev-mcp")
        assert tool is not None
        assert tool.name == "Shopify Dev MCP"
        
        # 2. Verify Scopes
        scope = inv.get_scope("shopify-dev-mcp", "search_docs_chunks")
        assert scope is not None
        assert scope.firearms_required is False
    
    asyncio.run(_test())

def test_search_docs_execution():
    async def _test():
        # 3. Test Handler Wiring
        inv = get_inventory()
        scope = inv.get_scope("shopify-dev-mcp", "search_docs_chunks")
        
        ctx = RequestContext(tenant_id="t_lab", env="dev", mode="lab", user_id="u1")
        input_data = SearchDocsInput(query="how to create product")
        
        # Mock the adapter interaction to avoid spawning real npx
        with patch("engines.connectors.shopify_dev.impl._adapter.call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = ["doc chunk 1", "doc chunk 2"]
            
            result = await scope.handler(ctx, input_data)
            
            assert result == ["doc chunk 1", "doc chunk 2"]
            mock_call.assert_called_once_with("search_docs_chunks", {"query": "how to create product"})

    asyncio.run(_test())
