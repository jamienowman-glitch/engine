"""Eval service orchestration."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from engines.eval.adapters import BedrockEvalAdapter, EvalAdapter, RagasEvalAdapter, VertexEvalAdapter
from engines.eval.schemas import EvalJob, EvalStatus
from engines.nexus.logging import ModelCallLog, PromptSnapshot


class EvalService:
    def __init__(
        self,
        adapters: Dict[str, EvalAdapter],
        model_call_logger=None,
    ) -> None:
        self._adapters = adapters
        self._jobs: Dict[str, EvalJob] = {}
        self._model_call_logger = model_call_logger

    def schedule_eval(
        self,
        input_ref: Dict[str, Any],
        eval_kind: str,
        backend: str,
        tenant_id: str,
        episode_id: Optional[str] = None,
        model_call_ids: Optional[List[str]] = None,
        prompt_snapshots: Optional[List[str]] = None,
    ) -> EvalJob:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        job = EvalJob(
            job_id=job_id,
            tenant_id=tenant_id,
            episode_id=episode_id,
            eval_kind=eval_kind,
            backend=backend,
            status=EvalStatus.scheduled,
            raw_payload=input_ref,
            model_call_ids=model_call_ids or [],
            prompt_snapshot_refs=prompt_snapshots or [],
            created_at=now,
            updated_at=now,
        )
        self._jobs[job_id] = job
        adapter = self._get_adapter(backend)
        backend_job_id = adapter.submit_job({"input_ref": input_ref, "eval_kind": eval_kind})
        job.status = EvalStatus.running
        job.updated_at = datetime.now(timezone.utc)
        # For this minimal implementation, fetch immediately to completion
        result = adapter.fetch_result(backend_job_id)
        job.scores = result.get("scores", {})
        job.status = EvalStatus.completed
        job.updated_at = datetime.now(timezone.utc)
        self._log_model_call(job, result)
        self._jobs[job_id] = job
        return job

    def get_eval_result(self, job_id: str) -> EvalJob:
        return self._jobs[job_id]

    def list_eval_for_episode(self, episode_id: str) -> List[EvalJob]:
        return [j for j in self._jobs.values() if j.episode_id == episode_id]

    def _get_adapter(self, backend: str) -> EvalAdapter:
        if backend not in self._adapters:
            raise ValueError(f"Unknown eval backend {backend}")
        return self._adapters[backend]

    def _log_model_call(self, job: EvalJob, result: Dict[str, Any]) -> None:
        if not self._model_call_logger:
            return
        prompt_text = result.get("prompt_text", "")
        model_id = result.get("model_id", job.backend)
        call = ModelCallLog(
            tenant_id=job.tenant_id,
            env=result.get("env", "dev"),
            model_id=model_id,
            purpose=f"eval:{job.eval_kind}",
            prompt=PromptSnapshot(text=prompt_text),
            output_dimensions=len(result.get("scores", {})),
            episode_id=job.episode_id,
        )
        self._model_call_logger(call)
