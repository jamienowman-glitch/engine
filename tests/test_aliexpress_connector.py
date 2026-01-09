import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.aliexpress.impl import calculate_freight, CalculateAliFreightInput

def test_aliexpress_flow():
    import asyncio
    asyncio.run(_async_test_aliexpress_flow())

async def _async_test_aliexpress_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.aliexpress.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.return_value = "ali_session_key"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"aeop_freight_calculate_result_for_buyer_d_t_o": {"freight": "5.00"}}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await calculate_freight(ctx, CalculateAliFreightInput(
            product_id="12345",
            country_code="US"
        ))
        
        # Verify Params
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["params"]["access_token"] == "ali_session_key"
        assert call_kwargs["base_url"] == "https://api-sg.aliexpress.com"
        
        # Verify Call
        args, kwargs = mock_client_instance.post.call_args
        assert args[0] == "/sync"
        assert kwargs["params"]["method"] == "aliexpress.logistics.buyer.freight.calculate"
        assert "12345" in kwargs["params"]["param_aeop_freight_calculate_for_buyer_d_t_o"]
        
        # Verify Result
        assert result["aeop_freight_calculate_result_for_buyer_d_t_o"]["freight"] == "5.00"
