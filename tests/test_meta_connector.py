import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.meta.impl import create_campaign, CreateMetaCampaignInput

def test_meta_flow():
    import asyncio
    asyncio.run(_async_test_meta_flow())

async def _async_test_meta_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.meta.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.side_effect = lambda k: "123456" if "account-id" in k else "token_abc"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "camp_123"}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await create_campaign(ctx, CreateMetaCampaignInput(
            name="Test Campaign",
            objective="OUTCOME_SALES"
        ))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer token_abc"
        assert call_kwargs["base_url"] == "https://graph.facebook.com/v19.0"
        
        # Verify Payload and Endpoint (Auto-added act_ prefix)
        mock_client_instance.post.assert_called_with("/act_123456/campaigns", json={
            "name": "Test Campaign",
            "objective": "OUTCOME_SALES",
            "status": "PAUSED",
            "special_ad_categories": []
        })
        
        # Verify Result
        assert result["id"] == "camp_123"
