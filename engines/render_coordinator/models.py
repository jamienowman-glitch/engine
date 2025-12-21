from __future__ import annotations
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

JobStatus = Literal["PENDING", "ASSIGNED", "RUNNING", "COMPLETED", "FAILED"]
WorkerStatus = Literal["IDLE", "BUSY", "OFFLINE"]

class Job(BaseModel):
    id: str
    plan: Dict[str, Any]
    status: JobStatus = "PENDING"
    worker_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    artifacts: List[str] = Field(default_factory=list)

class Worker(BaseModel):
    id: str
    status: WorkerStatus = "IDLE"
    last_heartbeat: float = Field(default_factory=time.time)
    current_job_id: Optional[str] = None
