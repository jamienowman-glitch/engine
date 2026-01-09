import asyncio
import os
from unittest.mock import patch
from engines.common.identity import RequestContext
from engines.connectors.shopify_dev.impl import SearchDocsInput, search_docs_chunks

# Patch to ensure connector is enabled
with patch.dict(os.environ, {"ENABLED_CONNECTORS": "shopify_dev"}):
    async def main():
        ctx = RequestContext(tenant_id="t_lab", env="dev", mode="lab", user_id="admin")
        
        # Query for scopes
        print("Querying Shopify Dev MCP for 'Admin API access scopes'...")
        try:
            # We use the handler directly which wraps the adapter
            result = await search_docs_chunks(ctx, SearchDocsInput(query="list of all Admin API access scopes"))
            
            # The result from mcp-server-shopify is likely a complex object or text.
            # We'll print a summary.
            print("--- Result Snippet ---")
            print(str(result)[:2000]) # Print first 2000 chars
            print("----------------------")
            
        except Exception as e:
            print(f"Error executing query: {e}")

    if __name__ == "__main__":
        asyncio.run(main())
