import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.printful.impl import list_orders, ListOrdersInput
from engines.connectors.printful.impl import generate_mockups, GenerateMockupsInput

def test_printful_flow():
    import asyncio
    asyncio.run(_async_test_printful_flow())

def test_mockup_generation():
    import asyncio
    asyncio.run(_async_test_mockup_generation())

async def _async_test_printful_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.printful.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        # Setup Secrets
        MockStore.return_value.get_secret.side_effect = lambda k: "pf-token" if "api-key" in k else "123"
        
        # Setup Mock HTTPX
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": [{"id": 101, "status": "draft"}]}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        
        MockClient.return_value = mock_client_instance
        
        # Execute
        result = await list_orders(ctx, ListOrdersInput(limit=5, status="draft"))
        
        # Verify Headers
        call_kwargs = MockClient.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer pf-token"
        assert call_kwargs["headers"]["X-PF-Store-Id"] == "123"
        assert call_kwargs["base_url"] == "https://api.printful.com"
        
        # Verify Endpoint Call
        mock_client_instance.get.assert_called_with("/orders", params={"limit": 5, "status": "draft"})
        
        # Verify Result
        assert result["result"][0]["id"] == 101

async def _async_test_mockup_generation():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    with patch("engines.connectors.printful.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep: # Skip waiting
        
        # Setup Mock Client
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        
        # Sequence of Responses:
        # 1. POST Create Task -> OK (task_key=abc)
        # 2. GET Task -> Pending
        # 3. GET Task -> Completed
        
        res1 = MagicMock()
        res1.json.return_value = {"result": {"task_key": "abc"}}
        res1.raise_for_status.return_value = None
        
        res2 = MagicMock()
        res2.json.return_value = {"result": {"status": "pending"}}
        res2.raise_for_status.return_value = None
        
        res3 = MagicMock()
        res3.json.return_value = {"result": {"status": "completed", "mockups": ["img1.jpg"]}}
        res3.raise_for_status.return_value = None
        
        # Assign side effects to methods
        mock_client_instance.post.return_value = res1
        mock_client_instance.get.side_effect = [res2, res3] # polling calls
        
        MockClient.return_value = mock_client_instance

        # Execute
        input_data = GenerateMockupsInput(
            variant_ids=[100],
            files=[{"image_url": "http://img", "placement": "default"}]
        )
        result = await generate_mockups(ctx, input_data)
        
        # Verify 
        assert result["result"]["status"] == "completed"
        assert result["result"]["mockups"][0] == "img1.jpg"
        
        # Verify Polling
        assert mock_client_instance.get.call_count == 2
        assert mock_client_instance.post.call_count == 1
