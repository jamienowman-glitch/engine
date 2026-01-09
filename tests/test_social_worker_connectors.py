import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.twitter.impl import post_tweet, PostTweetInput
from engines.connectors.pinterest.impl import create_pin, CreatePinterestPinInput
from engines.connectors.twitch.impl import create_clip, CreateTwitchClipInput

# Helper class to avoid AsyncMock contamination
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code
        self.content = b""
        self.headers = {}
    
    def json(self):
        return self._json
    
    def raise_for_status(self):
        pass

def test_social_worker_flow():
    import asyncio
    asyncio.run(_async_test_social_worker_flow())

async def _async_test_social_worker_flow():
    ctx = RequestContext(tenant_id="t_worker", env="dev", mode="lab", user_id="u1")
    
    # --- Twitter ---
    with patch("engines.connectors.twitter.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.twitter.impl.httpx.AsyncClient") as MockClient:
        
        MockStore.return_value.get_secret.return_value = "key"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        # Responses
        mock_client.post.return_value = MockResponse({"data": {"id": "tweet_1", "text": "hello"}})
        MockClient.return_value = mock_client
        
        await post_tweet(ctx, PostTweetInput(text="Hello World"))
        
        mock_client.post.assert_called_with("https://api.twitter.com/2/tweets", json={"text": "Hello World"})
        
        # Verify Auth was initialized (checked via MockClient call args in real life, sufficient here that it ran)

    # --- Pinterest (Organic) ---
    with patch("engines.connectors.pinterest.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.pinterest.impl.httpx.AsyncClient") as MockClient:
        
        MockStore.return_value.get_secret.return_value = "pin_tok"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        mock_client.post.return_value = MockResponse({"id": "pin_123"})
        MockClient.return_value = mock_client
        
        await create_pin(ctx, CreatePinterestPinInput(board_id="b1", title="Pin", media_url="img.jpg"))
        
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["board_id"] == "b1"
        assert kwargs["json"]["media_source"]["source_type"] == "image_url"

    # --- Twitch ---
    with patch("engines.connectors.twitch.impl.LocalSecretStore") as MockStore, \
         patch("engines.connectors.twitch.impl.httpx.AsyncClient") as MockClient:
         
        MockStore.return_value.get_secret.return_value = "tw_tok"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        # Sequence: GET /users (resolve ID) -> POST /clips
        mock_client.get.return_value = MockResponse({"data": [{"id": "user_99"}]})
        mock_client.post.return_value = MockResponse({"data": [{"id": "clip_abc"}]})
        
        MockClient.return_value = mock_client
        
        await create_clip(ctx, CreateTwitchClipInput(has_delay=True))
        
        mock_client.get.assert_called_with("/users")
        mock_client.post.assert_called_with("/clips", params={"broadcaster_id": "user_99", "has_delay": True})
