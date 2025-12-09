"""Eval backend adapters."""
from __future__ import annotations

from typing import Any, Dict, Protocol


class EvalAdapter(Protocol):
    def submit_job(self, payload: Dict[str, Any]) -> str:
        ...

    def fetch_result(self, backend_job_id: str) -> Dict[str, Any]:
        ...


class VertexEvalAdapter:
    def __init__(self, client: Any):
        self._client = client

    def submit_job(self, payload: Dict[str, Any]) -> str:
        return self._client.submit_job(payload)

    def fetch_result(self, backend_job_id: str) -> Dict[str, Any]:
        return self._client.fetch_result(backend_job_id)


class BedrockEvalAdapter:
    def __init__(self, client: Any):
        self._client = client

    def submit_job(self, payload: Dict[str, Any]) -> str:
        return self._client.submit_job(payload)

    def fetch_result(self, backend_job_id: str) -> Dict[str, Any]:
        return self._client.fetch_result(backend_job_id)


class RagasEvalAdapter:
    def __init__(self, client: Any):
        self._client = client

    def submit_job(self, payload: Dict[str, Any]) -> str:
        return self._client.submit_job(payload)

    def fetch_result(self, backend_job_id: str) -> Dict[str, Any]:
        return self._client.fetch_result(backend_job_id)
