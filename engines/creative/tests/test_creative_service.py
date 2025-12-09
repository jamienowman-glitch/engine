from __future__ import annotations

from engines.creative.schemas import QpuJobMetadata
from engines.creative.service import CreativeEvalService, QpuLoggingAdapter


def test_record_and_fetch_eval():
    svc = CreativeEvalService()
    ce = svc.record_eval("artefact-1", {"aesthetic": 0.8}, backend="imagen", tenant_id="t_demo")
    fetched = svc.fetch_eval("artefact-1")
    assert fetched is not None
    assert fetched.scores["aesthetic"] == 0.8


def test_qpu_logging_adapter_logs_events():
    logs = []

    def logger(evt):
        logs.append(evt)

    adapter = QpuLoggingAdapter(logger=logger)
    job = QpuJobMetadata(
        job_id="job1",
        backend="braket",
        tenant_id="t_demo",
        status="running",
    )
    adapter.log_job_start(job)
    job.status = "completed"
    adapter.log_job_result(job)
    assert logs[0]["event"] == "qpu_job_start"
    assert logs[1]["event"] == "qpu_job_result"
