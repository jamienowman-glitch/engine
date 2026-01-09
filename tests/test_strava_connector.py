import pytest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.strava.impl import get_athlete_stats, ReadAthleteInput

def test_strava_adapter_flow():
    import asyncio
    asyncio.run(_async_test_strava_adapter_flow())

async def _async_test_strava_adapter_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # Mock Everything
    with patch("engines.connectors.strava.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.strava.impl.StdioMCPAdapter") as MockAdapterClass, \
         patch("engines.connectors.strava.impl.open", new_callable=MagicMock) as mock_open, \
         patch("engines.connectors.strava.impl.os.path.exists") as mock_exists, \
         patch("engines.connectors.strava.impl.os.makedirs") as mock_makedirs, \
         patch("engines.connectors.strava.impl.subprocess.run") as mock_subprocess:
        
        # Setup Secrets
        MockStore.return_value.get_secret.side_effect = lambda k: "secret_val" if "strava" in k else None
        
        # Setup Adapter
        mock_adapter_instance = AsyncMock()
        mock_adapter_instance.call_tool.return_value = {"stats": "good"}
        MockAdapterClass.return_value = mock_adapter_instance
        
        # Simulate Driver NOT Exists (trigger clone)
        mock_exists.return_value = False
        
        # Execute
        await get_athlete_stats(ctx, ReadAthleteInput())
        
        # Verify Clone
        mock_subprocess.assert_called_with(
            ["git", "clone", "https://github.com/ctvidic/strava-mcp-server.git", os.path.expanduser("~/.northstar/drivers/strava")],
            check=True,
            capture_output=True
        )
        
        # Verify Config Write
        # Check that we opened the .env file for writing
        expected_env_path = os.path.join(os.path.expanduser("~/.northstar/drivers/strava"), "config", ".env")
        mock_open.assert_called_with(expected_env_path, "w")
        
        # Verify Adapter Init
        call_args = MockAdapterClass.call_args
        _, kwargs = call_args
        
        assert kwargs["command"] == "uv"
        assert "--with" in kwargs["args"]
        assert "fastmcp" in kwargs["args"]
        # Ensure path is absolute
        assert kwargs["args"][-1].startswith("/")
        assert kwargs["args"][-1].endswith("src/strava_server.py")
        
        # Verify Tool Call
        mock_adapter_instance.call_tool.assert_called_with("get_athlete_stats", {})
