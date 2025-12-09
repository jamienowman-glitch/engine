from engines.dataset.events.schemas import DatasetEvent
from engines.reactive.content.engine import watch


class DummyBackend:
    def __init__(self):
        self.events = []

    def write_event(self, event):
        self.events.append(event)
        return event

    def write_snippet(self, *args, **kwargs):
        return {}

    def get_latest_plan(self, *args, **kwargs):
        return None


def test_reactive_youtube_triggers(monkeypatch):
    backend = DummyBackend()
    monkeypatch.setattr("engines.logging.events.engine.get_backend", lambda: backend)
    monkeypatch.setattr("engines.chat.pipeline.get_backend", lambda: backend)
    event = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="content",
        agentId="connector",
        input={"url": "https://youtube.com/watch?v=123"},
        output={},
        analytics_event_type="content.published.youtube_video",
        metadata={"type": "content.published.youtube_video", "title": "Demo Vid"},
    )
    created = watch(event)
    assert len(created) >= 1
    assert backend.events, "expected reactive events to be logged"
    assert any(e.analytics_event_type.startswith("content.reactive") for e in created)
