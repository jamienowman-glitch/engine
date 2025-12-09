from fastapi.testclient import TestClient

from engines.chat import pipeline
from engines.chat.service import llm_client
from engines.chat.service.server import create_app


def test_http_thread_and_messages(monkeypatch) -> None:
    # Stub LLM streaming to avoid external calls
    monkeypatch.setattr(llm_client, "stream_chat", lambda **kwargs: iter(["hi there"]))
    monkeypatch.setattr(pipeline, "llm_client", llm_client)

    class StubBackend:
        def write_snippet(self, kind, doc, tags=None):
            return {"id": doc.id, "text": doc.text}

        def write_event(self, event):
            return {}

    monkeypatch.setattr(pipeline, "get_backend", lambda: StubBackend())

    client = TestClient(create_app())
    # create thread
    resp = client.post("/chat/threads", json={"participants": [{"id": "u1"}]})
    assert resp.status_code == 200
    thread_id = resp.json()["id"]
    # post message
    resp = client.post(f"/chat/threads/{thread_id}/messages", json={"sender": {"id": "u1"}, "text": "hello"})
    assert resp.status_code == 200
    # get messages includes user + agent orchestration reply
    resp = client.get(f"/chat/threads/{thread_id}/messages")
    msgs = resp.json()
    assert len(msgs) == 2
    assert "hi there" in msgs[1]["text"]
