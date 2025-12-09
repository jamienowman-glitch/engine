"""Creative eval and QPU logging services."""
from __future__ import annotations

from typing import Dict, Optional

from engines.creative.schemas import CreativeEval, QpuJobMetadata


class CreativeEvalService:
    def __init__(self, store=None):
        self._store = store or {}

    def record_eval(self, artefact_ref: str, scores: Dict[str, float], backend: str, tenant_id: str) -> CreativeEval:
        eval_id = f"{tenant_id}-{artefact_ref}"
        ce = CreativeEval(id=eval_id, tenant_id=tenant_id, artefact_ref=artefact_ref, backend=backend, scores=scores)
        self._store[eval_id] = ce
        return ce

    def fetch_eval(self, artefact_ref: str) -> Optional[CreativeEval]:
        return next((v for v in self._store.values() if v.artefact_ref == artefact_ref), None)

    def list_eval_by_episode(self, episode_id: str):
        return [v for v in self._store.values() if v.eval_payload_ref == episode_id]


class QpuLoggingAdapter:
    def __init__(self, logger=None):
        self._logger = logger

    def log_job_start(self, job: QpuJobMetadata):
        if self._logger:
            self._logger({"event": "qpu_job_start", "job_id": job.job_id, "backend": job.backend})
        return job

    def log_job_result(self, job: QpuJobMetadata):
        if self._logger:
            self._logger({"event": "qpu_job_result", "job_id": job.job_id, "backend": job.backend, "status": job.status})
        return job
