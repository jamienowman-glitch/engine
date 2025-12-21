import uuid
import time
from typing import Dict, Optional, List
from engines.render_coordinator.models import Job, Worker, JobStatus

class CoordinatorService:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._workers: Dict[str, Worker] = {}

    def register_worker(self, worker_id: str) -> Worker:
        if worker_id in self._workers:
            w = self._workers[worker_id]
            w.last_heartbeat = time.time()
            w.status = "IDLE" if not w.current_job_id else "BUSY"
            return w
        
        w = Worker(id=worker_id, status="IDLE")
        self._workers[worker_id] = w
        return w

    def submit_job(self, plan: dict) -> Job:
        job_id = uuid.uuid4().hex
        job = Job(id=job_id, plan=plan, status="PENDING")
        self._jobs[job_id] = job
        self._try_assign_jobs()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def _try_assign_jobs(self):
        # Naive scheduling
        pending = [j for j in self._jobs.values() if j.status == "PENDING"]
        idle_workers = [w for w in self._workers.values() if w.status == "IDLE"]
        
        for job, worker in zip(pending, idle_workers):
            job.status = "ASSIGNED"
            job.worker_id = worker.id
            
            worker.status = "BUSY"
            worker.current_job_id = job.id
            # in real world, we'd push to worker queue

_svc = None
def get_coordinator_service() -> CoordinatorService:
    global _svc
    if _svc is None:
        _svc = CoordinatorService()
    return _svc
