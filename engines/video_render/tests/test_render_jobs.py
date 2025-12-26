
import os
import pytest
from unittest.mock import patch, MagicMock

from engines.video_render.service import RenderService
from engines.video_render.jobs import InMemoryRenderJobRepository, VideoRenderJob
from engines.video_render.models import RenderRequest
from engines.media_v2.service import MediaService, set_media_service, InMemoryMediaRepository, LocalMediaStorage
from engines.video_timeline.service import TimelineService, set_timeline_service, InMemoryTimelineRepository

def setup_function():
    set_media_service(MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))

def _get_service(max_concurrent=10):
    svc = RenderService(job_repo=InMemoryRenderJobRepository())
    svc._max_concurrent_jobs = max_concurrent
    return svc

def _dummy_req(tenant="t1", project="p1"):
    return RenderRequest(
        tenant_id=tenant, env="dev", user_id="u1", project_id=project, 
        render_profile="social_1080p_h264", dry_run=False
    )

def test_idempotency_active_job():
    """Verify create_job returns existing active job if found."""
    service = _get_service()
    req = _dummy_req()
    
    with patch("engines.video_render.service.RenderService._build_plan", return_value=MagicMock(model_dump=lambda: {})):
         # First creation
         job1 = service.create_job(req)
         assert job1.status == "queued"
         
         # Second creation - should return same job (active)
         job2 = service.create_job(req)
         assert job2.id == job1.id
         assert job2.status == "queued"
         
         # Move to running
         job1.status = "running"
         service.job_repo.update(job1)
         
         # Third creation - should still return same job
         job3 = service.create_job(req)
         assert job3.id == job1.id
         assert job3.status == "running"

def test_cancel_job():
    """Verify cancellation flow."""
    service = _get_service()
    req = _dummy_req()
    
    with patch("engines.video_render.service.RenderService._build_plan", return_value=MagicMock(model_dump=lambda: {})):
        job = service.create_job(req)
        assert job.status == "queued"
        
        service.cancel_job(job.id)
        
        updated = service.job_repo.get(job.id)
        assert updated.status == "cancelled"
        
        # Try cancel again (idempotent/safe)
        service.cancel_job(job.id)
        updated2 = service.job_repo.get(job.id)
        assert updated2.status == "cancelled"

def test_resume_job():
    """Verify resume flow."""
    service = _get_service()
    req = _dummy_req()
    
    with patch("engines.video_render.service.RenderService._build_plan", return_value=MagicMock(model_dump=lambda: {})):
        job = service.create_job(req)
        # Manually fail it
        job.status = "failed"
        job.error_message = "boom"
        service.job_repo.update(job)
        
        # Resume
        resumed = service.resume_job(job.id)
        assert resumed.status == "queued"
        assert resumed.progress == 0.0
        assert resumed.error_message is None

def test_backpressure():
    """Verify max concurrent jobs limit."""
    service = _get_service(max_concurrent=2)
    req1 = _dummy_req(project="p1")
    req2 = _dummy_req(project="p2")
    req3 = _dummy_req(project="p3")
    
    with patch("engines.video_render.service.RenderService._build_plan", return_value=MagicMock(model_dump=lambda: {})):
        job1 = service.create_job(req1)
        job2 = service.create_job(req2)
        
        assert job1.status == "queued"
        assert job2.status == "queued"
        
        # Third one should fail
        with pytest.raises(RuntimeError, match="max concurrent render jobs reached"):
            service.create_job(req3)
