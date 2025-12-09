from __future__ import annotations

import os

import pytest

from engines.eval.service import EvalService
from engines.eval.schemas import EvalStatus


class DummyAdapter:
    def __init__(self, fail=False):
        self.fail = fail
        self.submits = []
        self.fetches = []

    def submit_job(self, payload):
        if self.fail:
            raise RuntimeError("submit failed")
        self.submits.append(payload)
        return "backend-1"

    def fetch_result(self, backend_job_id):
        if self.fail:
            raise RuntimeError("fetch failed")
        self.fetches.append(backend_job_id)
        return {"scores": {"quality": 0.9}, "model_id": "vertex-eval"}


def test_schedule_eval_lifecycle(monkeypatch):
    adapter = DummyAdapter()
    logged_calls = []

    def log_call(call):
        logged_calls.append(call)

    svc = EvalService(adapters={"vertex": adapter}, model_call_logger=log_call)
    job = svc.schedule_eval(
        input_ref={"model_call_id": "mc1"},
        eval_kind="rag_precision",
        backend="vertex",
        tenant_id="t_demo",
        episode_id="ep1",
        model_call_ids=["mc1"],
        prompt_snapshots=["ps1"],
    )

    assert job.status == EvalStatus.completed
    assert job.scores["quality"] == 0.9
    assert logged_calls and logged_calls[0].purpose == "eval:rag_precision"


def test_schedule_eval_handles_missing_adapter():
    svc = EvalService(adapters={}, model_call_logger=None)
    with pytest.raises(ValueError):
        svc.schedule_eval(
            input_ref={},
            eval_kind="rag_precision",
            backend="unknown",
            tenant_id="t_demo",
        )


def test_list_eval_for_episode_filters():
    adapter = DummyAdapter()
    svc = EvalService(adapters={"vertex": adapter})
    job1 = svc.schedule_eval(
        input_ref={},
        eval_kind="coherence",
        backend="vertex",
        tenant_id="t_demo",
        episode_id="ep1",
    )
    job2 = svc.schedule_eval(
        input_ref={},
        eval_kind="truthfulness",
        backend="vertex",
        tenant_id="t_demo",
        episode_id="ep2",
    )
    eps_jobs = svc.list_eval_for_episode("ep1")
    assert len(eps_jobs) == 1
    assert eps_jobs[0].job_id == job1.job_id
