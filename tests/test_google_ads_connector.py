import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.google_ads.impl import execute_gaql, ExecuteGAQLInput

def test_google_ads_adapter_flow():
    import asyncio
    asyncio.run(_async_test_google_ads_adapter_flow())

async def _async_test_google_ads_adapter_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    fake_yaml = "developer_token: test_token\nclient_id: test_id"
    
    with patch("engines.connectors.google_ads.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.google_ads.impl.StdioMCPAdapter") as MockAdapterClass, \
         patch("engines.connectors.google_ads.impl.open", new_callable=MagicMock) as mock_open, \
         patch("engines.connectors.google_ads.impl.os.makedirs") as mock_makedirs, \
         patch("engines.connectors.google_ads.impl.os.chmod") as mock_chmod:
        
        # Setup Secrets
        MockStore.return_value.get_secret.return_value = fake_yaml
        
        # Setup Adapter
        mock_adapter_instance = AsyncMock()
        mock_adapter_instance.call_tool.return_value = [{"campaign.name": "Test Campaign"}]
        MockAdapterClass.return_value = mock_adapter_instance
        
        # Execute
        input_data = ExecuteGAQLInput(
            query="SELECT campaign.name FROM campaign",
            customer_id="1234567890"
        )
        result = await execute_gaql(ctx, input_data)
        
        # Verify Result
        assert result[0]["campaign.name"] == "Test Campaign"
        
        # Verify File Write
        # We expect a file to be written to ~/.northstar/tmp/google-ads-t_verification.yaml
        expected_path = os.path.expanduser("~/.northstar/tmp/google-ads-t_verification.yaml")
        
        # Verify Adapter Init
        # The adapter should have been initialized with the correct env var pointing to that file
        call_args = MockAdapterClass.call_args
        assert call_args is not None
        _, kwargs = call_args
        
        assert kwargs["command"] == "uvx"
        assert kwargs["env"]["GOOGLE_ADS_CREDENTIALS"] == expected_path
        
        # Verify Tool Call
        mock_adapter_instance.call_tool.assert_called_with(
            "execute_gaql",
            {
                "query": "SELECT campaign.name FROM campaign",
                "customer_id": "1234567890"
            }
        )
