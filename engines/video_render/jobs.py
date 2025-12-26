from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from engines.config import runtime_config

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None


RenderStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
RenderJobType = Literal["full", "segment"]


def _uuid() -> str:
    return uuid.uuid4().hex


class VideoRenderJob(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: str
    render_profile: str
    job_type: RenderJobType = "full"
    status: RenderStatus = "queued"
    progress: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan_snapshot: Optional[Dict[str, Any]] = None
    result_asset_id: Optional[str] = None
    result_artifact_id: Optional[str] = None
    error_message: Optional[str] = None
    render_cache_key: Optional[str] = None
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    segment_index: Optional[int] = None
    segment_start_ms: Optional[float] = None
    segment_end_ms: Optional[float] = None
    overlap_ms: Optional[float] = None


class RenderJobRepository:
    def create(self, job: VideoRenderJob) -> VideoRenderJob:
        raise NotImplementedError

    def get(self, job_id: str) -> Optional[VideoRenderJob]:
        raise NotImplementedError

    def list(self, tenant_id: str, env: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None) -> List[VideoRenderJob]:
        raise NotImplementedError

    def update(self, job: VideoRenderJob) -> VideoRenderJob:
        raise NotImplementedError

    def find_by_cache_key(self, tenant_id: str, cache_key: str, job_type: Optional[RenderJobType] = None, statuses: Optional[List[str]] = None) -> Optional[VideoRenderJob]:
        raise NotImplementedError


class InMemoryRenderJobRepository(RenderJobRepository):
    def __init__(self) -> None:
        self.jobs: Dict[str, VideoRenderJob] = {}

    def create(self, job: VideoRenderJob) -> VideoRenderJob:
        self.jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[VideoRenderJob]:
        return self.jobs.get(job_id)

    def list(self, tenant_id: str, env: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None) -> List[VideoRenderJob]:
        results = [j for j in self.jobs.values() if j.tenant_id == tenant_id]
        if env:
            results = [j for j in results if j.env == env]
        if status:
            results = [j for j in results if j.status == status]
        if project_id:
            results = [j for j in results if j.project_id == project_id]
        return sorted(results, key=lambda j: j.created_at, reverse=True)

    def update(self, job: VideoRenderJob) -> VideoRenderJob:
        self.jobs[job.id] = job
        return job

    def find_by_cache_key(self, tenant_id: str, cache_key: str, job_type: Optional[RenderJobType] = None, statuses: Optional[List[str]] = None) -> Optional[VideoRenderJob]:
        target_statuses = set(statuses) if statuses else {"succeeded"}
        for job in self.jobs.values():
            if job.tenant_id != tenant_id:
                continue
            if job.render_cache_key != cache_key:
                continue
            if job.status not in target_statuses:
                continue
            if job_type and job.job_type != job_type:
                continue
            return job
        return None


class FirestoreRenderJobRepository(RenderJobRepository):
    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        project = runtime_config.get_firestore_project()
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _col(self, tenant_id: str):
        return self._client.collection(f"video_render_jobs_{tenant_id}")

    def create(self, job: VideoRenderJob) -> VideoRenderJob:
        self._col(job.tenant_id).document(job.id).set(job.model_dump())
        return job

    def get(self, job_id: str) -> Optional[VideoRenderJob]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return None
        snap = self._col(tenant).document(job_id).get()
        return VideoRenderJob(**snap.to_dict()) if snap and snap.exists else None

    def list(self, tenant_id: str, env: Optional[str] = None, status: Optional[str] = None, project_id: Optional[str] = None) -> List[VideoRenderJob]:
        query = self._col(tenant_id).where("tenant_id", "==", tenant_id)
        if env:
            query = query.where("env", "==", env)
        if status:
            query = query.where("status", "==", status)
        if project_id:
            query = query.where("project_id", "==", project_id)
        docs = query.stream()
        return sorted([VideoRenderJob(**d.to_dict()) for d in docs], key=lambda j: j.created_at, reverse=True)

    def update(self, job: VideoRenderJob) -> VideoRenderJob:
        self._col(job.tenant_id).document(job.id).set(job.model_dump())
        return job

    def find_by_cache_key(self, tenant_id: str, cache_key: str, job_type: Optional[RenderJobType] = None, statuses: Optional[List[str]] = None) -> Optional[VideoRenderJob]:
        query = self._col(tenant_id).where("render_cache_key", "==", cache_key)
        if statuses:
            query = query.where("status", "in", statuses)
        else:
            query = query.where("status", "==", "succeeded")
        
        if job_type:
            query = query.where("job_type", "==", job_type)
        docs = query.limit(1).stream()
        for d in docs:
            return VideoRenderJob(**d.to_dict())
        return None
