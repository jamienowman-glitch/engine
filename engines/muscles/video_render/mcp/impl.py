from typing import Any, List, Optional, Dict
from pydantic import BaseModel

from engines.common.identity import RequestContext
from engines.nexus.hardening.gate_chain import GateChain
from engines.muscle.video_render.service import get_render_service
from engines.muscle.video_render.models import RenderRequest

class SubmitInput(BaseModel):
    project_id: str
    render_profile: str
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    # Optional overrides
    start_ms: Optional[float] = None
    end_ms: Optional[float] = None
    overlap_ms: Optional[float] = None
    segment_index: Optional[int] = None

class StatusInput(BaseModel):
    job_id: str

async def handle_submit(ctx: RequestContext, args: SubmitInput) -> Any:
    # 1. Enforce Policy
    GateChain().run(ctx, action="video.render.submit", subject_id=args.project_id, subject_type="video_project", surface="video_render")
    
    svc = get_render_service()
    
    # Construct RenderRequest. 
    # Logic: Wrapper maps input model to service domain model.
    req = RenderRequest(
        tenant_id=args.tenant_id,
        env=args.env,
        user_id=args.user_id or ctx.user_id,
        project_id=args.project_id,
        render_profile=args.render_profile,
        start_ms=args.start_ms,
        end_ms=args.end_ms,
        overlap_ms=args.overlap_ms,
        segment_index=args.segment_index
    )
    
    job = svc.create_job(req)
    return job

async def handle_status(ctx: RequestContext, args: StatusInput) -> Any:
    # 1. Enforce Policy
    GateChain().run(ctx, action="video.render.status", subject_id=args.job_id, subject_type="render_job", surface="video_render")
    
    svc = get_render_service()
    
    # RenderService doesn't expose get(id) on self, but on job_repo.
    # We can access job_repo directly as it's public.
    job = svc.job_repo.get(args.job_id)
    
    if not job:
        raise ValueError("Job not found")
        
    return job
