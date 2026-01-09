import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.klaviyo.impl import get_account_details, GetAccountDetailsInput

def test_klaviyo_adapter_call():
    import asyncio
    asyncio.run(_async_test_klaviyo_adapter_call())

async def _async_test_klaviyo_adapter_call():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # Mock Secrets
    with patch("engines.connectors.klaviyo.impl.LocalSecretStore") as MockStore:
        MockStore.return_value.get_secret.return_value = "pk_12345"
        
        # Mock Adapter
        with patch("engines.connectors.klaviyo.impl.StdioMCPAdapter") as MockAdapterClass:
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.call_tool.return_value = {"id": "123", "company_name": "Test Co"}
            MockAdapterClass.return_value = mock_adapter_instance
            
            # Execute
            result = await get_account_details(ctx, GetAccountDetailsInput())
            
            # Verify
            assert result["company_name"] == "Test Co"
            MockAdapterClass.assert_called_with(
                command="uvx",
                args=["klaviyo-mcp-server@latest"],
                env={
                    "PRIVATE_API_KEY": "pk_12345",
                    "READ_ONLY": "false",
                    "ALLOW_USER_GENERATED_CONTENT": "false"
                }
            )
            mock_adapter_instance.call_tool.assert_called_with("get_account_details", {})
