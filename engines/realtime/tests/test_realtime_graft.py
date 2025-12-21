"""Tests for Graft Gestures and Replay (Step 6)."""
import pytest
from fastapi.testclient import TestClient
from engines.chat.service.server import app
from engines.realtime.isolation import registry
from engines.canvas_stream.replay import replay_service
from engines.chat.service.transport_layer import bus

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_data():
    registry.clear()
    registry.register_thread("t_demo", "th-gestures")
    yield

def test_ws_gesture_passthrough():
    # We need a token for the WS
    from engines.identity.jwt_service import default_jwt_service
    # Mock secrets handling implicitly done if default_jwt_service works or we patch env
    import os
    from unittest.mock import patch
    
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "secret"}):
        svc = default_jwt_service()
        token = svc.issue_token({
            "sub": "user-1",
            "default_tenant_id": "t_demo",
            "tenant_ids": ["t_demo"],
            "role_map": {"t_demo": "member"}
        })
        
        with client.websocket_connect(f"/ws/chat/th-gestures?token={token}") as websocket:
            # Consume presence
            websocket.receive_json()
            
            # Send gesture
            gesture_payload = {
                "type": "gesture",
                "data": {"x": 10, "y": 20, "kind": "cursor"}
            }
            websocket.send_json(gesture_payload)
            
            # Since WS subscribes to bus, we should receive our own gesture back!
            # The bus subscriber in ws_transport converts it to StreamEvent.
            
            # We need to wait a bit or just read next message.
            # Using loop to skip pings if any
            found = False
            for _ in range(3):
                import json
                try:
                    data = websocket.receive_json()
                    # It comes back as a StreamEvent JSON string or dict?
                    # ws_transport `broadcast_event` sends `event.json()`.
                    # TestClient receive_json parses that JSON string IF the server sent text.
                    # Yes.
                    
                    # We look for type="gesture"
                    if data.get("type") == "gesture":
                        assert data["data"]["x"] == 10
                        assert data["meta"]["persist"] == "never"
                        found = True
                        break
                except:
                   pass
            assert found, "Did not receive echoed gesture"

def test_replay_service_stub():
    # Just verify the stub contract matches
    snapshot = replay_service.generate_keyframe("c1", 100)
    assert snapshot["rev"] == 100
    assert "nodes" in snapshot
