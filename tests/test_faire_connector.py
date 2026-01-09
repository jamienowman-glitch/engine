import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.faire.impl import list_products, ListFaireProductsInput

def test_faire_flow():
    import asyncio
    asyncio.run(_async_test_faire_flow())

async def _async_test_faire_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.faire.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.return_value = "faire_abc"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"products": [{"id": "p_1"}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await list_products(ctx, ListFaireProductsInput(page=1))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["X-Faire-Access-Token"] == "faire_abc"
        assert call_kwargs["base_url"] == "https://www.faire.com/api/v2"
        
        # Verify Call
        mock_client_instance.get.assert_called_with("/products", params={"page": 1, "limit": 50})
        
        # Verify Result
        assert result["products"][0]["id"] == "p_1"
