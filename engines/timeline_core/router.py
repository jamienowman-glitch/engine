from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from engines.common.identity import RequestContext, get_request_context
from engines.timeline_core.models import (
    Task, Dependency, TaskStatus, 
    GanttView, ContentPlanPayload
)
from engines.timeline_core.service import TimelineService
from engines.plan_of_work.models import PlanOfWork
from engines.boq_quantities.models import BoQModel

router = APIRouter(prefix="/timeline", tags=["timeline"])

# Global In-Memory Service (Singleton for MVP)
# In real prod, this would be injected or attached to app state with DB backend.
_SERVICE = TimelineService()

def get_service() -> TimelineService:
    return _SERVICE

class DependencyRequest(BaseModel):
    from_id: str
    to_id: str

@router.post("/tasks", response_model=str)
async def create_task(
    task: Task,
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    # Enforce context on task object?
    # Service checks exact match. Caller must set tenant_id/env on Task to match header.
    # Ideally we'd overwrite it from context to be safe.
    
    # Overwriting for convenience/security:
    task.tenant_id = ctx["tenant_id"]
    task.env = ctx["env"]
    
    try:
        return service.create_task(ctx, task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks", response_model=List[Task])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    group_id: Optional[str] = None,
    lane_id: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    filters = {}
    if status: filters["status"] = status
    if group_id: filters["group_id"] = group_id
    if lane_id: filters["lane_id"] = lane_id
    if tags: filters["tags"] = tags
    
    return service.list_tasks(ctx, filters)

@router.get("/tasks/{task_id}", response_model=Optional[Task])
async def get_task(
    task_id: str,
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    task = service.get_task(ctx, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/dependencies", status_code=204)
async def add_dependency(
    dep: DependencyRequest,
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    try:
        service.add_dependency(ctx, dep.from_id, dep.to_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/view/gantt", response_model=GanttView)
async def get_gantt_view(
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    # Filters currently not exposed in view endpoint, but could be.
    return service.get_gantt_view(ctx)

@router.post("/import/plan", response_model=List[str])
async def import_plan_of_work(
    plan: PlanOfWork,
    project_start_ts: datetime,
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    return service.import_from_plan_of_work(ctx, plan, project_start_ts)

@router.post("/import/boq", response_model=List[str])
async def import_boq(
    boq: BoQModel,
    project_start_ts: datetime,
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    return service.import_from_boq(ctx, boq, project_start_ts)

@router.post("/import/content", response_model=List[str])
async def import_content_plan(
    plan: ContentPlanPayload,
    request_context: RequestContext = Depends(get_request_context),
    service: TimelineService = Depends(get_service)
):
    ctx = {"tenant_id": request_context.tenant_id, "env": request_context.env}
    return service.import_from_content_plan(ctx, plan)
