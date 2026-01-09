import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.pinterest.impl import create_campaign, CreatePinterestCampaignInput

def test_pinterest_flow():
    import asyncio
    asyncio.run(_async_test_pinterest_flow())

async def _async_test_pinterest_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.pinterest.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.side_effect = lambda k: "123" if "account-id" in k else "pin_token"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": [{"data": {"id": "camp_1"}}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await create_campaign(ctx, CreatePinterestCampaignInput(
            name="Pin Campaign",
            objective_type="WEB_CONVERSION"
        ))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer pin_token"
        assert call_kwargs["base_url"] == "https://api.pinterest.com/v5"
        
        # Verify Payload (Array for Bulk Create)
        mock_client_instance.post.assert_called_with("/ad_accounts/123/campaigns", json=[{
            "name": "Pin Campaign",
            "objective_type": "WEB_CONVERSION",
            "status": "ACTIVE"
        }])
        
        # Verify Result
        assert result["items"][0]["data"]["id"] == "camp_1"
