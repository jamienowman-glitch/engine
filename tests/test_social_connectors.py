import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from engines.common.identity import RequestContext
from engines.connectors.youtube.impl import upload_video, UploadYouTubeVideoInput
from engines.connectors.tiktok.impl import post_video, PostTikTokVideoInput
from engines.connectors.instagram.impl import publish_media, PublishInstagramMediaInput

def test_social_flow():
    import asyncio
    asyncio.run(_async_test_social_flow())

async def _async_test_social_flow():
    ctx = RequestContext(tenant_id="t_verification", env="dev", mode="lab", user_id="u1")
    
    # --- YouTube ---
    with patch("engines.connectors.youtube.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient: # This mocks ALL clients
        
        MockStore.return_value.get_secret.return_value = "yt_tok"
        
        # Setup specific responses based on call order is tricky with one MockClient for multiple instances.
        # Strategy: Mock instances returned by __aenter__
        
        # We have TWO clients in upload_video: 1 (downloader), 2 (uploader)
        
        # Client 1: Downloader
        mock_dl_instance = AsyncMock() # The object AsyncClient() returns
        mock_dl_ctx = AsyncMock() # The object __aenter__ returns
        mock_dl_resp = MagicMock()
        mock_dl_resp.content = b"VIDEO_BYTES"
        mock_dl_ctx.get.return_value = mock_dl_resp
        mock_dl_instance.__aenter__.return_value = mock_dl_ctx
        mock_dl_instance.__aexit__.return_value = None
        
        # Client 2: Uploader
        mock_up_instance = AsyncMock()
        mock_up_ctx = AsyncMock()
        mock_up_resp = MagicMock()
        mock_up_resp.json.return_value = {"id": "vid_123"}
        mock_up_ctx.post.return_value = mock_up_resp
        mock_up_instance.__aenter__.return_value = mock_up_ctx
        mock_up_instance.__aexit__.return_value = None
        
        # Side effect on the Class constructor
        MockClient.side_effect = [mock_dl_instance, mock_up_instance, mock_dl_instance, mock_up_instance]
        
        await upload_video(ctx, UploadYouTubeVideoInput(video_url="http://vid.mp4", title="Title", description="Desc"))
        
        # Verify against the Context Objects, not the instances
        mock_dl_ctx.get.assert_called_with("http://vid.mp4")
        args, kwargs = mock_up_ctx.post.call_args
        assert kwargs["params"]["part"] == "snippet,status"
        assert "metadata.json" in str(kwargs["files"]["body"])

    # --- TikTok ---
    with patch("engines.connectors.tiktok.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        MockStore.return_value.get_secret.return_value = "tt_tok"
        
        # Client 1: Downloader (reused logic)
        mock_dl_inst = AsyncMock()
        mock_dl_ctx = AsyncMock()
        mock_dl_ctx.get.return_value = MagicMock(content=b"VIDEO_BYTES")
        mock_dl_inst.__aenter__.return_value = mock_dl_ctx
        mock_dl_inst.__aexit__.return_value = None
        
        # Client 2: TikTok Init
        mock_init_inst = AsyncMock()
        mock_init_ctx = AsyncMock()
        mock_init_resp = MagicMock()
        mock_init_resp.json.return_value = {"data": {"upload_url": "http://upload.tiktok", "publish_id": "p_1"}}
        mock_init_ctx.post.return_value = mock_init_resp
        mock_init_inst.__aenter__.return_value = mock_init_ctx
        mock_init_inst.__aexit__.return_value = None
        
        # Client 3: Uploader (PUT)
        mock_put_inst = AsyncMock()
        mock_put_ctx = AsyncMock()
        mock_put_ctx.put.return_value = MagicMock()
        mock_put_inst.__aenter__.return_value = mock_put_ctx
        mock_put_inst.__aexit__.return_value = None
        
        MockClient.side_effect = [mock_dl_inst, mock_init_inst, mock_put_inst]
        
        await post_video(ctx, PostTikTokVideoInput(video_url="http://tt.mp4", title="Caption"))
        
        mock_init_ctx.post.assert_called()
        mock_put_ctx.put.assert_called_with("http://upload.tiktok", content=b"VIDEO_BYTES", headers={"Content-Type": "video/mp4", "Content-Length": "11"})

    # --- Instagram ---
    with patch("engines.connectors.instagram.impl.LocalSecretStore") as MockStore, \
         patch("httpx.AsyncClient") as MockClient:
        
        MockStore.return_value.get_secret.return_value = "ig_tok"
        
        mock_ig_inst = AsyncMock()
        mock_ig_ctx = AsyncMock()
        
        # Helper class to avoid AsyncMock contamination
        class MockResponse:
            def __init__(self, json_data, status_code=200):
                self._json = json_data
                self.status_code = status_code
                self.content = b""
            
            def json(self):
                return self._json
            
            def raise_for_status(self):
                pass

        # Response 1: Create Container
        resp1 = MockResponse({"id": "cont_123"})
        
        # Response 2: Publish
        resp2 = MockResponse({"id": "media_published"})
        
        # Configure INSTANCE because implementation uses 'client.post' directly
        mock_ig_inst.post.side_effect = [resp1, resp2]
        
        # GET for status checks
        status_resp = MockResponse({"status_code": "FINISHED"})
        mock_ig_inst.get.return_value = status_resp
        
        # Ensure context manager works (even if unused var)
        mock_ig_inst.__aenter__.return_value = mock_ig_ctx
        mock_ig_inst.__aexit__.return_value = None
        
        MockClient.side_effect = [mock_ig_inst] # Only one client used
        
        await publish_media(ctx, PublishInstagramMediaInput(media_url="http://reel.mp4", media_type="REELS"))
        
        # Verify calls on INSTANCE
        assert mock_ig_inst.post.call_count == 2
        
        # Check params for REELS
        call1 = mock_ig_inst.post.call_args_list[0]
        assert call1.kwargs["params"]["media_type"] == "REELS"
        
        # Check polling
        mock_ig_inst.get.assert_called_with("/cont_123", params={"fields": "status_code"})
        
        # Call executed above, verification follows

        
        # All verification done above against mock_ig_inst
