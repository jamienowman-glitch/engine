import pytest
from unittest.mock import AsyncMock, patch
from engines.canvas_stream.service import publish_gesture, GestureEvent
from engines.feature_flags.models import FeatureFlags
from engines.chat.service.transport_layer import bus

@pytest.fixture
def clean_bus():
    bus.messages = {}
    return bus

@pytest.mark.asyncio
def test_gesture_fanout_enabled(clean_bus):
    import asyncio
    
    async def run():
        # Mock flags: visible + logging
        mock_flags = FeatureFlags(
            tenant_id="t_test", env="dev",
            ws_enabled=True,
            sse_enabled=True,
            gesture_logging=True,
            visibility_mode="public"
        )
        
        with patch("engines.canvas_stream.service.get_feature_flags", new=AsyncMock(return_value=mock_flags)):
            gesture = GestureEvent(kind="caret", payload={"x": 1}, actor_id="u1")
            
            result = await publish_gesture("c1", gesture, "t_test", "dev")
            
            assert result is True
            # Check bus
            msgs = bus.get_messages("c1")
            assert len(msgs) == 1
            assert "gesture" in msgs[0].text
            
    asyncio.run(run())

@pytest.mark.asyncio
def test_gesture_fanout_disabled(clean_bus):
    import asyncio
    
    async def run():
        # Mock flags: private (no fanout) but logging off
        mock_flags = FeatureFlags(
            tenant_id="t_test", env="dev",
            ws_enabled=True,
            sse_enabled=True,
            gesture_logging=False,
            visibility_mode="private"
        )
        
        with patch("engines.canvas_stream.service.get_feature_flags", new=AsyncMock(return_value=mock_flags)):
            gesture = GestureEvent(kind="caret", payload={"x": 1}, actor_id="u1")
            
            result = await publish_gesture("c1", gesture, "t_test", "dev")
            
            # Result false because both logging off and visibility private (logic in service says if not log AND private -> drop)
            assert result is False
            
            msgs = bus.get_messages("c1")
            assert len(msgs) == 0
            
    asyncio.run(run())
