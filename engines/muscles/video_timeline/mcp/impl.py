from typing import Any, List, Optional, Dict, Literal, Union
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.common.error_envelope import error_response, ErrorEnvelope
from engines.nexus.hardening.gate_chain import GateChain
from engines.muscle.video_timeline.service import get_timeline_service
from engines.muscle.video_timeline.models import VideoProject, Sequence, Track, Clip

# --- Read Models ---
class ReadInput(BaseModel):
    operation: Literal["get_project", "list_sequences", "list_tracks", "list_clips"]
    project_id: Optional[str] = None
    sequence_id: Optional[str] = None
    track_id: Optional[str] = None
    tenant_id: Optional[str] = None

# --- Write Models ---
class WriteInput(BaseModel):
    operation: Literal["trim_clip", "split_clip", "move_clip"]
    clip_id: str
    # Trim args
    new_in_ms: Optional[float] = None
    new_out_ms: Optional[float] = None
    ripple: bool = False
    # Split args
    split_time_ms: Optional[float] = None
    # Move args
    new_start_ms: Optional[float] = None
    target_track_id: Optional[str] = None

# --- Handlers ---

async def handle_read(ctx: RequestContext, args: ReadInput) -> Any:
    # 1. Enforce Policy via GateChain
    # If overlay binds this action, firearms check happens. Default is Open.
    GateChain().run(ctx, action="video.timeline.read", subject_id=args.project_id or args.sequence_id or "unknown", subject_type="video_project", surface="video_timeline")
    
    svc = get_timeline_service()
    
    try:
        if args.operation == "get_project":
            if not args.project_id:
                raise ValueError("project_id required")
            return svc.get_project(args.project_id)
            
        elif args.operation == "list_sequences":
            if not args.project_id:
                raise ValueError("project_id required")
            return svc.list_sequences_for_project(args.project_id)
            
        elif args.operation == "list_tracks":
            if not args.sequence_id:
                raise ValueError("sequence_id required")
            return svc.list_tracks_for_sequence(args.sequence_id)
            
        elif args.operation == "list_clips":
            if not args.track_id:
                raise ValueError("track_id required")
            return svc.list_clips_for_track(args.track_id)
            
        else:
            raise ValueError(f"Unknown operation: {args.operation}")
            
    except Exception as e:
        # Catch-all to wrap in ErrorEnvelope if not handled by GateChain exceptions
        # But GateChain raises HTTPException usually.
        # Here we just re-raise or let generic handler catch.
        # Standard says "One true ErrorEnvelope pattern". 
        # Usually Gateway's exception handler wraps uncaught exceptions.
        # If we want to return explicit envelope structure here:
        raise e 


async def handle_write(ctx: RequestContext, args: WriteInput) -> Any:
    # 1. Enforce Policy
    GateChain().run(ctx, action="video.timeline.write", subject_id=args.clip_id, subject_type="video_clip", surface="video_timeline")
    
    svc = get_timeline_service()
    
    if args.operation == "trim_clip":
        if args.new_in_ms is None or args.new_out_ms is None:
            raise ValueError("trim_clip requires new_in_ms and new_out_ms")
        return svc.trim_clip(args.clip_id, args.new_in_ms, args.new_out_ms, args.ripple)
        
    elif args.operation == "split_clip":
        if args.split_time_ms is None:
            raise ValueError("split_clip requires split_time_ms")
        return svc.split_clip(args.clip_id, args.split_time_ms)
        
    elif args.operation == "move_clip":
        if args.new_start_ms is None:
            raise ValueError("move_clip requires new_start_ms")
        return svc.move_clip(args.clip_id, args.new_start_ms, args.target_track_id, args.ripple)
        
    else:
        raise ValueError(f"Unknown operation: {args.operation}")
