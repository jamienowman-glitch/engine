import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from engines.connectors.generic_remote.impl import proxy_call, RemoteCallPayload
from engines.common.identity import RequestContext

def run_async(coro):
    return asyncio.run(coro)

def test_proxy_call_success():
    """Test that proxy_call correctly forwards request with auth."""
    
    async def _test():
        # Mock Context
        ctx = RequestContext(
            tenant_id="t_tenant123",
            mode="saas",
            user_id="user-456",
            project_id="proj-789"
        )
        
        # Mock Payload
        payload = RemoteCallPayload(
            tool="my.remote.tool.search",
            arguments={"q": "northstar"}
        )
        
        # Mock Secrets
        with patch("engines.connectors.generic_remote.impl._get_secrets") as mock_get_secrets:
            # Configured for tenant
            mock_get_secrets.return_value.get_secret.side_effect = lambda k: {
                "conn-generic-remote-url-t_tenant123": "https://remote-mcp.com",
                "conn-generic-remote-token-t_tenant123": "secret-token"
            }.get(k)
            
            # Mock HTTPX
            with patch("httpx.AsyncClient") as MockClient:
                mock_http = AsyncMock()
                MockClient.return_value.__aenter__.return_value = mock_http
                
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"result": "remote data"}
                # Important: mock_http.post is an AsyncMock, so it returns a coroutine.
                # But since we use AsyncMock, it returns a coroutine that resolves to return_value.
                mock_http.post.return_value = mock_response
                
                # Execute
                result = await proxy_call(ctx, payload)
                
                # Verify
                assert result == {"result": "remote data"}
                
                # Verify Call Args
                mock_http.post.assert_called_once()
                call_args = mock_http.post.call_args
                url = call_args[0][0]
                kwargs = call_args[1]
                
                assert url == "https://remote-mcp.com/tools/call"
                assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
                assert kwargs["headers"]["X-Tenant-ID"] == "t_tenant123"
                assert kwargs["json"]["tool_id"] == "my.remote.tool"
                assert kwargs["json"]["scope_name"] == "search"
                assert kwargs["json"]["arguments"] == {"q": "northstar"}

    run_async(_test())

def test_proxy_call_missing_config():
    """Test failure when config is missing."""
    async def _test():
        ctx = RequestContext(tenant_id="t_1", mode="lab", user_id="u1")
        payload = RemoteCallPayload(tool="t", arguments={})
        
        with patch("engines.connectors.generic_remote.impl._get_secrets") as mock_get_secrets:
            mock_get_secrets.return_value.get_secret.return_value = None
            
            with pytest.raises(ValueError, match="Remote MCP URL not configured"):
                await proxy_call(ctx, payload)

    run_async(_test())
