import json

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app


def test_websocket_broadcast() -> None:
    app = create_app()
    client = TestClient(app)

    # create a thread via HTTP
    resp = client.post("/chat/threads", json={"participants": [{"id": "u1"}]})
    thread_id = resp.json()["id"]

    with client.websocket_connect(f"/ws/chat/{thread_id}") as ws1, client.websocket_connect(
        f"/ws/chat/{thread_id}"
    ) as ws2:
        ws1.send_json({"type": "message", "sender_id": "u1", "text": "hi ws"})
        data = ws2.receive_text()
        payload = json.loads(data)
        assert payload["type"] == "message"
        assert payload["data"]["text"] == "hi ws"
