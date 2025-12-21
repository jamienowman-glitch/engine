from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from engines.video_render.models import RenderRequest, RenderResult, ChunkPlanRequest, RenderSegment, SegmentJobsRequest, StitchRequest
from engines.video_render.jobs import VideoRenderJob
from engines.video_render.service import get_render_service

router = APIRouter(prefix="/video", tags=["video_render"])


@router.post("/render", response_model=RenderResult)
def render(req: RenderRequest):
    try:
        return get_render_service().render(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected errors bubbled to client
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render/dry-run", response_model=RenderResult)
def render_dry_run(req: RenderRequest):
    req.dry_run = True
    return render(req)


@router.post("/render/chunks/plan", response_model=list[RenderSegment])
def plan_render_chunks(req: ChunkPlanRequest):
    try:
        return get_render_service().plan_segments(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/render/chunks/stitch", response_model=RenderResult)
def stitch_render_chunks(req: StitchRequest):
    try:
        return get_render_service().stitch_segments(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Render jobs
@router.post("/render/jobs", response_model=VideoRenderJob)
def create_render_job(req: RenderRequest):
    try:
        return get_render_service().create_job(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/render/jobs/{job_id}", response_model=VideoRenderJob)
def get_render_job(job_id: str):
    job = get_render_service().job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/render/jobs", response_model=list[VideoRenderJob])
def list_render_jobs(tenant_id: str, env: str | None = None, status: str | None = None, project_id: str | None = None):
    return get_render_service().list_jobs(tenant_id=tenant_id, env=env, status=status, project_id=project_id)


@router.post("/render/jobs/segments", response_model=list[VideoRenderJob])
def create_segment_render_jobs(req: SegmentJobsRequest):
    try:
        return get_render_service().create_segment_jobs(req.render_request, req.segments)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/render/jobs/chunked", response_model=list[VideoRenderJob])
def create_chunked_jobs(req: ChunkPlanRequest):
    try:
        return get_render_service().create_chunked_jobs(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/render/jobs/{job_id}/run", response_model=VideoRenderJob)
def run_render_job(job_id: str):
    try:
        return get_render_service().run_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render/jobs/{job_id}/cancel", response_model=VideoRenderJob)
def cancel_render_job(job_id: str):
    job = get_render_service().job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    job.status = "cancelled"
    job.updated_at = datetime.utcnow()
    return get_render_service().job_repo.update(job)
