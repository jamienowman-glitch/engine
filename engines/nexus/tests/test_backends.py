from __future__ import annotations

import os

import pytest

from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.nexus.backends import get_backend
from engines.nexus.schemas import NexusDocument, NexusKind


class DummyCollection:
    def __init__(self):
        self.writes = {}
        self.adds = []
        self._docs = []
        self._document_store = {}

    def document(self, doc_id):
        self._last_doc_id = doc_id
        return self

    def set(self, payload):
        self.writes[payload["id"]] = payload
        self._document_store[payload["id"]] = payload

    def add(self, payload):
        self.adds.append(payload)

    def where(self, *args, **kwargs):
        return self

    def limit(self, _):
        return self

    def order_by(self, *_):
        return self

    def stream(self):
        class D:
            def __init__(self, did, text):
                self.id = did
                self._text = text

            def to_dict(self):
                return {"text": self._text}

        return [D("d1", "hello")]

    def get(self):
        data = self._document_store.get(self._last_doc_id)
        if data is None:
            return type("Obj", (), {"exists": False})()
        return type(
            "Obj",
            (),
            {
                "exists": True,
                "to_dict": lambda self=data: data,
            },
        )()


class DummyClient:
    def __init__(self):
        self.collections = {"nexus_snippets_t_demo": DummyCollection(), "nexus_events_t_demo": DummyCollection()}

    def collection(self, name):
        if name not in self.collections:
            self.collections[name] = DummyCollection()
        return self.collections[name]


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("NEXUS_BACKEND", "firestore")
    monkeypatch.setenv("TENANT_ID", "t_demo")
    monkeypatch.setenv("ENV", "dev")
    runtime_config.config_snapshot.cache_clear()  # type: ignore


def test_factory_returns_firestore():
    backend = get_backend(client=DummyClient())
    assert backend.__class__.__name__ == "FirestoreNexusBackend"


def test_write_and_query(monkeypatch):
    client = DummyClient()
    backend = get_backend(client=client)
    doc = NexusDocument(id="abc", text="hello")
    backend.write_snippet(NexusKind.data, doc, tags=["a"])
    evt = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="chat",
        agentId="agent1",
        input={},
        output={},
    )
    backend.write_event(evt)
    hits = backend.query_by_tags(NexusKind.data, tags=["a"])
    assert hits and hits[0].text == "hello"
