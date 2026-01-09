import asyncio
import os
from unittest.mock import patch
from engines.mcp_gateway.inventory import get_inventory
from engines.workbench.dynamic_loader import loader

def test_real_shopify_loading():
    async def _test():
        # Enable just the shopify connector
        with patch.dict(os.environ, {"ENABLED_CONNECTORS": "shopify"}):
            loader.reload()
            
            inv = get_inventory()
            tool = inv.get_tool("shopify")
            assert tool is not None
            assert tool.name == "Shopify Admin"
            
            # Verify some key scopes exist
            assert inv.get_scope("shopify", "graphql_proxy") is not None
            assert inv.get_scope("shopify", "read_products") is not None
            assert inv.get_scope("shopify", "write_orders") is not None
            
            print("Shopify Connector loaded successfully with scopes.")

    asyncio.run(_test())
