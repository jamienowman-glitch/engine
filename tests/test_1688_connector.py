import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.c1688.impl import search_products, Search1688Input

def test_1688_flow():
    import asyncio
    asyncio.run(_async_test_1688_flow())

async def _async_test_1688_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.c1688.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.return_value = "apify_token_123"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = [{"title": "Wholesale T-Shirt", "price": "10.00"}]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await search_products(ctx, Search1688Input(url="https://www.1688.com/search.html?k=shirt"))
        
        # Verify Call
        mock_client_instance.post.assert_called_with(
            "https://api.apify.com/v2/acts/ecomscrape~1688-product-details-page-scraper/run-sync-get-dataset-items",
            json={"startUrls": [{"url": "https://www.1688.com/search.html?k=shirt"}]},
            params={"token": "apify_token_123"},
            timeout=60.0
        )
        
        # Verify Result
        assert result[0]["title"] == "Wholesale T-Shirt"
