import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.obs.impl import start_stream, ControlStreamInput

def test_obs_adapter_call():
    import asyncio
    asyncio.run(_async_test_obs_adapter_call())

async def _async_test_obs_adapter_call():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # Mock Secrets
    with patch("engines.connectors.obs.impl.LocalSecretStore") as MockStore:
        MockStore.return_value.get_secret.return_value = "secret123"
        
        # Mock Adapter
        with patch("engines.connectors.obs.impl.StdioMCPAdapter") as MockAdapterClass:
            mock_adapter_instance = AsyncMock()
            mock_adapter_instance.call_tool.return_value = {"status": "ok"}
            MockAdapterClass.return_value = mock_adapter_instance
            
            # Execute
            await start_stream(ctx, ControlStreamInput(action="start"))
            
            # Verify
            MockAdapterClass.assert_called_with(
                command="npx",
                args=["-y", "obs-mcp@latest"],
                env={"OBS_WEBSOCKET_PASSWORD": "secret123"}
            )
            mock_adapter_instance.call_tool.assert_called_with("StartStream", {})
