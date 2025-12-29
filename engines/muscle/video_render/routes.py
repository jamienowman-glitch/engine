from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.video_render.models import (
    RenderRequest,
    RenderResult,
    ChunkPlanRequest,
    RenderSegment,
    SegmentJobsRequest,
    StitchRequest,
)
from engines.video_render.jobs import VideoRenderJob
from engines.video_render.service import get_render_service


def _enforce_render_guard(
    request_context: RequestContext,
    auth_context: AuthContext,
    *,
    tenant_id: Optional[str] = None,
    env: Optional[str] = None,
) -> None:
    require_tenant_membership(auth_context, request_context.tenant_id)
    assert_context_matches(
        request_context,
        tenant_id=tenant_id,
        env=env,
        project_id=request_context.project_id,
    )

router = APIRouter(prefix="/video", tags=["video_render"])


@router.post("/render", response_model=RenderResult)
def render(
    req: RenderRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    try:
        return get_render_service().render(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - unexpected errors bubbled to client
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render/dry-run", response_model=RenderResult)
def render_dry_run(
    req: RenderRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    req.dry_run = True
    try:
        return get_render_service().render(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render/chunks/plan", response_model=list[RenderSegment])
def plan_render_chunks(
    req: ChunkPlanRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    try:
        return get_render_service().plan_segments(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/render/chunks/stitch", response_model=RenderResult)
def stitch_render_chunks(
    req: StitchRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    try:
        return get_render_service().stitch_segments(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Render jobs
@router.post("/render/jobs", response_model=VideoRenderJob)
def create_render_job(
    req: RenderRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    try:
        return get_render_service().create_job(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/render/jobs/{job_id}", response_model=VideoRenderJob)
def get_render_job(
    job_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(request_context, auth_context)
    job = get_render_service().job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/render/jobs", response_model=list[VideoRenderJob])
def list_render_jobs(
    tenant_id: str,
    env: str | None = None,
    status: str | None = None,
    project_id: str | None = None,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(request_context, auth_context, tenant_id=tenant_id, env=env)
    return get_render_service().list_jobs(tenant_id=tenant_id, env=env, status=status, project_id=project_id)


@router.post("/render/jobs/segments", response_model=list[VideoRenderJob])
def create_segment_render_jobs(
    req: SegmentJobsRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.render_request.tenant_id,
        env=req.render_request.env,
    )
    try:
        return get_render_service().create_segment_jobs(req.render_request, req.segments)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/render/jobs/chunked", response_model=list[VideoRenderJob])
def create_chunked_jobs(
    req: ChunkPlanRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(
        request_context,
        auth_context,
        tenant_id=req.tenant_id,
        env=req.env,
    )
    try:
        return get_render_service().create_chunked_jobs(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/render/jobs/{job_id}/run", response_model=VideoRenderJob)
def run_render_job(
    job_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(request_context, auth_context)
    try:
        return get_render_service().run_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/render/jobs/{job_id}/cancel", response_model=VideoRenderJob)
def cancel_render_job(
    job_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_render_guard(request_context, auth_context)
    job = get_render_service().job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    job.status = "cancelled"
    job.updated_at = datetime.utcnow()
    return get_render_service().job_repo.update(job)
