from fastapi.testclient import TestClient

from engines.chat.service.server import create_app


def test_sse_streams_message() -> None:
    client = TestClient(create_app())
    resp = client.post("/chat/threads", json={"participants": [{"id": "u1"}]})
    thread_id = resp.json()["id"]

    # start SSE stream
    with client.stream("GET", f"/sse/chat/{thread_id}") as stream:
        # post message
        client.post(f"/chat/threads/{thread_id}/messages", json={"sender": {"id": "u1"}, "text": "hello sse"})
        # read a couple of lines from stream
        line = next(stream.iter_lines())
        assert b"event: message" in line
        data_line = next(stream.iter_lines())
        assert b"hello sse" in data_line
