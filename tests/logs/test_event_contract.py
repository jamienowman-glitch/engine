import pytest

from engines.common.identity import RequestContext
from engines.dataset.events.schemas import DatasetEvent
from engines.nexus.vector_explorer.service import VectorExplorerService
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore
from engines.nexus.embedding import EmbeddingAdapter, EmbeddingResult
from engines.realtime.contracts import (
    StreamEvent,
    RoutingKeys,
    ActorType,
    EventIds,
    EventMeta,
    EventPriority,
    PersistPolicy,
)


class _DummyRepo:
    def get(self, tenant_id: str, env: str, item_id: str):
        return None

    def list_filtered(self, **kwargs):
        return []

    def write_record(self, tenant_id: str, record: dict) -> None:
        return None


class _DummyVectorStore(ExplorerVectorStore):
    def upsert(self, *args, **kwargs) -> None:
        return None

    def query(self, *args, **kwargs):
        return []

    def query_by_datapoint_id(self, *args, **kwargs):
        return []


class _DummyEmbedder(EmbeddingAdapter):
    def embed_text(self, text: str, model_id=None, context=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.0], model_id="stub")

    def embed_image(self, image_uri: str, model_id=None, context=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.0], model_id="stub")

    def embed_image_bytes(self, image_bytes: bytes, model_id=None, context=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.0], model_id="stub")


class _DummyBudgetService:
    def record_usage(self, context: RequestContext, events=None):
        return None


def test_dataset_event_requires_required_scope_fields(monkeypatch):
    monkeypatch.setenv("EVENT_CONTRACT_ENFORCE", "1")
    with pytest.raises(ValueError) as exc:
        DatasetEvent(
            tenantId="t_demo",
            env="dev",
            surface="chat",
            agentId="agent",
            input={},
            output={},
        )
    assert "project_id" in str(exc.value)
    assert "run_id" in str(exc.value)
    assert "step_id" in str(exc.value)


def test_dataset_event_accepts_complete_scope(monkeypatch):
    monkeypatch.setenv("EVENT_CONTRACT_ENFORCE", "1")
    event = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        mode="dev",
        surface="chat",
        agentId="agent",
        input={},
        output={},
        project_id="p_demo",
        run_id="run1",
        step_id="step1",
        traceId="trace1",
        requestId="req1",
    )
    assert event.project_id == "p_demo"
    assert event.run_id == "run1"


def test_stream_event_requires_scope(monkeypatch):
    monkeypatch.setenv("EVENT_CONTRACT_ENFORCE", "1")
    with pytest.raises(ValueError) as exc:
        StreamEvent(
            type="event",
            routing=RoutingKeys(
                tenant_id="t_demo",
                env="dev",
                thread_id="thread",
                actor_id="actor",
                actor_type=ActorType.HUMAN,
            ),
            ids=EventIds(request_id="req1"),
            data={},
        )
    assert "routing.mode" in str(exc.value)
    assert "run_id" in str(exc.value)
    assert "step_id" in str(exc.value)


def test_stream_event_accepts_complete_scope(monkeypatch):
    monkeypatch.setenv("EVENT_CONTRACT_ENFORCE", "1")
    routing = RoutingKeys(
        tenant_id="t_demo",
        env="dev",
        mode="dev",
        thread_id="thread",
        actor_id="actor",
        actor_type=ActorType.HUMAN,
        project_id="p_demo",
        surface_id="surf_demo",
    )
    event = StreamEvent(
        type="event",
        routing=routing,
        ids=EventIds(request_id="req1", run_id="run1", step_id="step1"),
        data={"ok": True},
        trace_id="req1",
        meta=EventMeta(
            priority=EventPriority.INFO,
            persist=PersistPolicy.ALWAYS,
        ),
    )
    assert event.ids.step_id == "step1"


def test_vector_explorer_requires_real_logger(monkeypatch):
    monkeypatch.setenv("EVENT_CONTRACT_ENFORCE", "1")
    with pytest.raises(RuntimeError):
        VectorExplorerService(
            repository=_DummyRepo(),
            vector_store=_DummyVectorStore(),
            embedder=_DummyEmbedder(),
            budget_service=_DummyBudgetService(),
        )
