# Muscle Scope Templates

Use these templates when implementing wrapper files (`impl.py`).

## 0. Commons Matches
Standard imports for all wrappers.

```python
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field
from engines.common.identity import RequestContext
from engines.nexus.hardening.gate_chain import GateChain
# Import your specific service factory here
# from engines.muscle.<muscle_id>.service import get_service
```

## 1. READ Scope (Synchronous)
Used for `get_`, `list_`, or analysis operations that return immediately.
Typically safe, but still gated by GateChain.

```python
class ReadInput(BaseModel):
    operation: str = Field(..., description="Sub-operation: 'get_project', 'list_items', etc.")
    # Common IDs
    project_id: Optional[str] = None
    item_id: Optional[str] = None
    # Filters
    limit: int = 10

async def handle_read(ctx: RequestContext, args: ReadInput) -> Any:
    # 1. Enforce Policy
    # For Lists: subject_id is usually None or Parent ID
    subject = args.item_id or args.project_id
    
    GateChain().run(
        ctx, 
        action="<namespace>.read", 
        subject_id=subject,
        subject_type="<resource_type>", # e.g. video_project
        surface="<muscle_id>"
    )
    
    svc = get_service()
    
    # 2. Dispatch
    if args.operation == "get_project":
        if not args.project_id:
            raise ValueError("project_id required")
        return svc.get_project(args.project_id)
        
    elif args.operation == "list_items":
        return svc.list_items(limit=args.limit)
        
    else:
        raise ValueError(f"Unknown operation: {args.operation}")
```

## 2. WRITE Scope (Synchronous)
Used for immediate mutations (create, update, delete, trim, split).
Requires stricter Pydantic validation.

```python
class WriteInput(BaseModel):
    operation: str = Field(..., description="'create', 'update', 'delete'")
    target_id: str
    payload: Dict[str, Any] = {}

async def handle_write(ctx: RequestContext, args: WriteInput) -> Any:
    # 1. Enforce Policy
    GateChain().run(
        ctx, 
        action="<namespace>.write", 
        subject_id=args.target_id, 
        subject_type="<resource_type>", 
        surface="<muscle_id>" # e.g. video_timeline
    )
    
    svc = get_service()
    
    if args.operation == "update":
        return svc.update_item(args.target_id, args.payload)
    # ...
```

## 3. SUBMIT Scope (Asynchronous Job)
Used for long-running tasks like Rendering. Returns a Job ID immediately.

```python
class SubmitInput(BaseModel):
    project_id: str
    profile: str
    # Other rendering params

async def handle_submit(ctx: RequestContext, args: SubmitInput) -> Any:
    # 1. Enforce Policy
    GateChain().run(
        ctx, 
        action="<namespace>.submit", 
        subject_id=args.project_id, 
        subject_type="video_project", 
        surface="<muscle_id>"
    )
    
    svc = get_service()
    
    # 2. Map to Domain Request
    job = svc.create_job(
        user_id=ctx.user_id,
        project_id=args.project_id,
        profile=args.profile
    )
    
    # 3. Return Job ID
    return {"job_id": job.id, "status": job.status}
```

## 4. STATUS Scope (Job Polling)
Used to check status of async jobs. Usually lightweight policy.

```python
class StatusInput(BaseModel):
    job_id: str

async def handle_status(ctx: RequestContext, args: StatusInput) -> Any:
    # 1. Enforce Policy (Optional but recommended for strict multi-tenant isolation)
    GateChain().run(
        ctx, 
        action="<namespace>.status", 
        subject_id=args.job_id, 
        subject_type="render_job", 
        surface="<muscle_id>"
    )
    
    svc = get_service()
    
    job = svc.get_job(args.job_id)
    if not job:
        return None # OR raise 404 exception if wrapper standard prefers
        
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "result_url": job.url if job.status == "DONE" else None
    }
```
