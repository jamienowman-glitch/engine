import asyncio
import os
import sys
from unittest.mock import patch

# Ensure repo root is in path
sys.path.append(os.getcwd())

from engines.common.identity import RequestContext
from engines.connectors.shopify_dev.impl import SearchDocsInput, search_docs_chunks
from engines.mcp_gateway.inventory import get_inventory
from engines.workbench.dynamic_loader import loader

async def run_queries():
    # Load inventory to ensure connector is ready
    loader.load_all()
    
    ctx = RequestContext(tenant_id="t_lab", env="dev", mode="lab", user_id="admin")
    
    queries = [
        "graphql mutation create article blog seo image",
        "graphql mutation create product media alt text accessibility",
        "shopify analytics graphql api",
        "graphql mutation update theme asset section"
    ]
    
    print("--- Starting Shopify Advanced Research ---")
    
    for q in queries:
        print(f"\n>>> Querying: '{q}' ...")
        try:
            # We call the handler directly. Ensure ENABLED_CONNECTORS includes shopify_dev
            result = await search_docs_chunks(ctx, SearchDocsInput(query=q))
            
            # Result is likely a list of strings (chunks).
            if isinstance(result, list):
                for i, chunk in enumerate(result[:2]): # Print first 2 chunks
                    print(f"--- Chunk {i+1} ---")
                    print(chunk[:500] + "..." if len(chunk) > 500 else chunk)
                    print("----------------")
            else:
                print(str(result)[:500])
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Patch environment to enable connector
    with patch.dict(os.environ, {"ENABLED_CONNECTORS": "shopify_dev"}):
        asyncio.run(run_queries())
