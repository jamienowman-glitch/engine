import pytest
from engines.render_coordinator.service import CoordinatorService

def test_job_assignment():
    svc = CoordinatorService()
    
    # 1. Register Worker
    w1 = svc.register_worker("w1")
    assert w1.status == "IDLE"
    
    # 2. Submit Job
    job = svc.submit_job({"cmd": "ffmpeg ..."})
    
    assert job.status == "ASSIGNED"
    assert job.worker_id == "w1"
    
    # Verify Worker State
    w1_ref = svc._workers["w1"]
    assert w1_ref.status == "BUSY"
    assert w1_ref.current_job_id == job.id

def test_job_pending_if_no_worker():
    svc = CoordinatorService()
    job = svc.submit_job({})
    assert job.status == "PENDING"
    assert job.worker_id is None
