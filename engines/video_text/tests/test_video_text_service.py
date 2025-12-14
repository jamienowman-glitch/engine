from unittest.mock import MagicMock
from engines.video_text.service import VideoTextService
from engines.video_text.models import TextRenderRequest
from engines.media_v2.models import MediaAsset

def test_render_text_basic():
    # Mock media service
    mock_media = MagicMock()
    mock_asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="image", source_uri="/tmp/out.png")
    mock_media.register_remote.return_value = mock_asset
    
    service = VideoTextService(media_service=mock_media)
    
    req = TextRenderRequest(
        tenant_id="t1", 
        env="dev", 
        text="Hello World",
        font_size_px=50,
        color_hex="#FF0000"
    )
    
    # We expect this to use fallback font (Arial) if Roboto Flex missing
    # or just work if fallback works.
    resp = service.render_text_image(req)
    
    assert resp.asset_id == "a1"
    assert resp.width > 0
    assert resp.height > 0
    
    # Verify media call
    mock_media.register_remote.assert_called_once()
    args = mock_media.register_remote.call_args[1] if mock_media.register_remote.call_args.kwargs else mock_media.register_remote.call_args[0][0]
    # Check args
    if hasattr(args, "kind"):
        assert args.kind == "image"

def test_render_empty_text():
    service = VideoTextService(media_service=MagicMock())
    req = TextRenderRequest(tenant_id="t1", env="dev", text="")
    try:
        service.render_text_image(req)
    except ValueError:
        pass
    else:
        assert False, "Should raise ValueError"
