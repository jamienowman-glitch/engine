import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.prodigi.impl import get_quote, GetQuoteInput

def test_prodigi_flow():
    import asyncio
    asyncio.run(_async_test_prodigi_flow())

async def _async_test_prodigi_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.prodigi.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.return_value = "prod_key"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"outcome": "Created", "quotes": [{"cost": 10.00}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await get_quote(ctx, GetQuoteInput(
            destinationCountryCode="US",
            items=[{"sku": "PAP-12x18", "copies": 1}]
        ))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["X-API-Key"] == "prod_key"
        assert call_kwargs["base_url"] == "https://api.prodigi.com/v4.0"
        
        # Verify Payload
        mock_client_instance.post.assert_called_with("/quotes", json={
            "destinationCountryCode": "US",
            "currencyCode": "USD",
            "items": [{"sku": "PAP-12x18", "copies": 1}]
        })
        
        # Verify Result
        assert result["quotes"][0]["cost"] == 10.00
