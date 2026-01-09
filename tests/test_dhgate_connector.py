import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.dhgate.impl import search_products, SearchDHgateInput

def test_dhgate_flow():
    import asyncio
    asyncio.run(_async_test_dhgate_flow())

async def _async_test_dhgate_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.dhgate.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.return_value = "dh_token"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"item": [{"name": "Wedding Dress"}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await search_products(ctx, SearchDHgateInput(keyword="dress"))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer dh_token"
        assert call_kwargs["base_url"] == "https://api.dhgate.com/v1"
        
        # Verify Call
        mock_client_instance.get.assert_called_with("/search/list", params={"q": "dress", "pageNo": 1, "pageSize": 20})
        
        # Verify Result
        assert result["item"][0]["name"] == "Wedding Dress"
