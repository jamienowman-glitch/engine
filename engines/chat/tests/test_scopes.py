import asyncio

from engines.chat.contracts import ChatScope, Contact
from engines.chat.pipeline import process_message
from engines.common.identity import RequestContext


class DummyBackend:
    def __init__(self):
        self.snippets = []
        self.events = []

    def write_snippet(self, kind, doc, tags=None):
        self.snippets.append({"kind": kind.value, "doc": doc, "tags": tags or []})
        return {}

    def write_event(self, event):
        self.events.append(event)
        return {}

    def get_latest_plan(self, *args, **kwargs):
        return None


class DummyPiiResult:
    def __init__(self):
        self.pii_flags = []
        self.clean_text = ""
        self.policy = None


def test_scoped_message_logs_scope(monkeypatch):
    backend = DummyBackend()
    monkeypatch.setattr("engines.chat.pipeline.get_backend", lambda: backend)
    monkeypatch.setattr("engines.logging.events.engine.get_backend", lambda: backend)
    monkeypatch.setattr(
        "engines.guardrails.pii_text.engine.run", lambda req: DummyPiiResult()
    )
    scope = ChatScope(kind="federation", target_id="fed_landing_pages")
    msgs = asyncio.run(
        process_message(
            "t1",
            Contact(id="u1"),
            "hello scoped",
            scope=scope,
            context=RequestContext(tenant_id="t_scope", env="dev", request_id="req-scope"),
        )
    )
    assert len(backend.snippets) == 1
    tags = backend.snippets[0]["tags"]
    assert "federation" in tags and "fed_landing_pages" in tags
    # Logging recorded scope
    assert backend.events, "expected log event"
    logged = backend.events[-1]
    assert logged.input.get("scope", {}).get("kind") == "federation"
    assert msgs[0].scope == scope
