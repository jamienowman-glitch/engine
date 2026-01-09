import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.adzuna.impl import search_jobs, SearchAdzunaJobsInput
from engines.connectors.linkedin.impl import share_update, ShareLinkedInUpdateInput

# Helper class to avoid AsyncMock contamination
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
    
    def json(self):
        return self._json
    
    def raise_for_status(self):
        pass

def test_job_flow():
    import asyncio
    asyncio.run(_async_test_job_flow())

async def _async_test_job_flow():
    ctx = RequestContext(tenant_id="t_job", env="dev", mode="lab", user_id="u1")
    
    # --- Adzuna ---
    with patch("engines.connectors.adzuna.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.adzuna.impl.httpx.AsyncClient") as MockClient:
        
        MockStore.return_value.get_secret.return_value = "adzuna_key"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = MockResponse({"results": []})
        MockClient.return_value = mock_client
        
        await search_jobs(ctx, SearchAdzunaJobsInput(what="Python", where="London"))
        
        # Verify call
        args, kwargs = mock_client.get.call_args
        assert args[0] == "/jobs/gb/search/1"
        assert kwargs["params"]["what"] == "Python"
        assert kwargs["params"]["where"] == "London"
        assert kwargs["params"]["app_id"] == "adzuna_key"

    # --- LinkedIn ---
    with patch("engines.connectors.linkedin.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.linkedin.impl.httpx.AsyncClient") as MockClient:
         
        MockStore.return_value.get_secret.return_value = "li_tok"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        # 1. GET /me (return ID 123)
        # 2. POST /ugcPosts
        mock_client.get.return_value = MockResponse({"id": "123"})
        mock_client.post.return_value = MockResponse({"id": "urn:li:share:999"})
        
        MockClient.return_value = mock_client
        
        await share_update(ctx, ShareLinkedInUpdateInput(text="New Job!", url="http://site.com"))
        
        # Check GET /me called
        mock_client.get.assert_called_with("/me")
        
        # Check POST payload
        post_call = mock_client.post.call_args
        payload = post_call.kwargs["json"]
        assert payload["author"] == "urn:li:person:123"
        assert payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] == "New Job!"
        assert payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] == "ARTICLE"
