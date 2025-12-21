"""Health Probe for K8s/GCP."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])

class HealthStatus(BaseModel):
    status: str
    version: str = "0.0.1"
    
@router.get("/health", response_model=HealthStatus)
def health_check():
    return HealthStatus(status="ok")

@router.get("/ready", response_model=HealthStatus)
def readiness_check():
    # In future: check DB/Redis connection
    return HealthStatus(status="ok")
