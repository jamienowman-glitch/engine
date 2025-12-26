import pytest
from engines.common.identity import RequestContext
from engines.dataset.events.schemas import DatasetEvent
from engines.logging import audit as audit_module
from engines.logging.events.engine import run
from engines.logging.event_log import default_event_logger, EventLogEntry
from engines.privacy.train_prefs import TrainingPreferenceService, set_training_pref_service
from engines.logging import events as logging_events
from unittest import mock


class _StubBackend:
    def __init__(self):
        self.events = []

    def write_event(self, event):
        self.events.append(event)
        return {"status": "stubbed"}


def test_logging_engine_stub_accepts_event() -> None:
    # Ensure clean prefs for determinism
    set_training_pref_service(TrainingPreferenceService())
    stub_backend = _StubBackend()
    logging_events.engine.get_backend = lambda: stub_backend  # type: ignore[attr-defined]
    ev = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="web",
        agentId="agent1",
        input={"msg": "hi"},
        output={"resp": "ok"},
    )
    res = run(ev)
    assert res["status"] == "accepted"
    assert ev.train_ok is True
    assert "flags" in ev.pii_flags
    assert stub_backend.events


def test_logging_engine_respects_train_opt_out() -> None:
    svc = TrainingPreferenceService()
    svc.set_user_opt_out("t_demo", "dev", "agent1", True)
    set_training_pref_service(svc)
    stub_backend = _StubBackend()
    logging_events.engine.get_backend = lambda: stub_backend  # type: ignore[attr-defined]
    ev = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="web",
        agentId="agent1",
        input={"msg": "hi"},
        output={"resp": "ok"},
    )
    run(ev)
    assert ev.train_ok is False


def test_trace_id_attached():
    with mock.patch(
        "engines.logging.event_log.log_dataset_event",
        return_value={"status": "accepted"},
    ) as log_event:
        entry = EventLogEntry(
            event_type="raw_asset_registered",
            asset_type="raw_asset",
            asset_id="asset-1",
            tenant_id="t_demo",
            request_id="req-100",
            trace_id="trace-100",
        )
        default_event_logger(entry)
        assert log_event.called
        dataset_event = log_event.call_args[0][0]
        assert dataset_event.metadata["request_id"] == "req-100"
        assert dataset_event.metadata["trace_id"] == "trace-100"


def test_emit_audit_event_includes_trace_and_actor(monkeypatch):
    captured: list[DatasetEvent] = []

    def fake_run(event: DatasetEvent) -> dict:
        captured.append(event)
        return {"status": "accepted"}

    monkeypatch.setattr(audit_module, "_audit_logger", fake_run)

    ctx = RequestContext(tenant_id="t_demo",
        env="dev",
        user_id="u_user",
        request_id="req-999",
    )
    audit_module.emit_audit_event(ctx, action="audit_test", surface="audit_test")

    assert captured
    event = captured[0]
    assert event.metadata["request_id"] == "req-999"
    assert event.metadata["trace_id"] == "req-999"
    assert event.metadata["actor_type"] == "human"
    assert event.traceId == "req-999"
    assert event.requestId == "req-999"
    assert event.actorType == "human"


def test_emit_audit_event_failure(monkeypatch):
    def fail(event: DatasetEvent) -> dict:
        return {"status": "error", "error": "boom"}

    monkeypatch.setattr(audit_module, "_audit_logger", fail)

    ctx = RequestContext(tenant_id="t_demo",
        env="dev",
        user_id="u_user",
        request_id="req-500",
    )
    with pytest.raises(RuntimeError) as excinfo:
        audit_module.emit_audit_event(ctx, action="audit_test", surface="audit_test")
    assert "boom" in str(excinfo.value)


def test_audit_logger_failure_not_silent(monkeypatch):
    stub_backend = _StubBackend()

    def fail(event):
        raise RuntimeError("boom")

    stub_backend.write_event = fail
    monkeypatch.setattr(logging_events.engine, "get_backend", lambda: stub_backend)
    ev = DatasetEvent(
        tenantId="t_demo",
        env="dev",
        surface="web",
        agentId="agent1",
        input={"msg": "hi"},
        output={"resp": "ok"},
    )
    result = run(ev)
    assert result["status"] == "error"
    assert "boom" in result["error"]
