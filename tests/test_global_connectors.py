import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.faire.impl import search_retailer_products, SearchFaireRetailerInput
from engines.connectors.fashiongo.impl import search_apparel, SearchFashionGoInput
from engines.connectors.tundra.impl import search_wholesale, SearchTundraInput
from engines.connectors.joor.impl import list_designers, ListJoorDesignersInput

def test_global_sourcing_flow():
    import asyncio
    asyncio.run(_async_test_global_sourcing_flow())

async def _async_test_global_sourcing_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # --- Test Faire Detailer ---
    with patch("engines.connectors.faire.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        MockStore.return_value.get_secret.return_value = "faire_tok"
        mock_response = MagicMock()
        mock_response.json.return_value = {"products": [{"id": "p1"}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        MockClient.return_value = mock_client
        
        await search_retailer_products(ctx, SearchFaireRetailerInput(query="candle", min_moq=5))
        
        # Verify Params
        mock_client.get.assert_called_with("/products", params={
            "page": 1, "limit": 50, "state": "ACTIVE", "lifecycle_state": "PUBLISHED",
            "q": "candle", "minimum_order_quantity": 5
        })

    # --- Test FashionGo ---
    with patch("engines.connectors.fashiongo.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        MockStore.return_value.get_secret.return_value = "fg_tok"
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response # Reuse mock response structure
        MockClient.return_value = mock_client
        
        await search_apparel(ctx, SearchFashionGoInput(keyword="dress"))
        
        mock_client.get.assert_called_with("/v1/items", params={"q": "dress", "page": 1})

    # --- Test Tundra ---
    with patch("engines.connectors.tundra.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        MockStore.return_value.get_secret.return_value = "tun_tok"
        MockClient.return_value = mock_client
        
        await search_wholesale(ctx, SearchTundraInput(query="toy"))
        
        mock_client.get.assert_called_with("/v2/products", params={"q": "toy", "page": 1})

    # --- Test JOOR ---
    with patch("engines.connectors.joor.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        MockStore.return_value.get_secret.return_value = "joor_tok"
        MockClient.return_value = mock_client
        
        await list_designers(ctx, ListJoorDesignersInput())
        
        mock_client.get.assert_called_with("/designers", params={"page": 1})
