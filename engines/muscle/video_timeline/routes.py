from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.video_timeline.models import Clip, FilterStack, Sequence, Track, Transition, VideoProject, ParameterAutomation
from engines.video_timeline.service import get_timeline_service

router = APIRouter(prefix="/video", tags=["video_timeline"])


def _enforce_timeline_guard(
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


def _not_found(name: str):
    raise HTTPException(status_code=404, detail=f"{name} not found")


# Projects
@router.post("/projects", response_model=VideoProject)
def create_project(
    project: VideoProject,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=project.tenant_id,
        env=project.env,
    )
    return get_timeline_service().create_project(project)


@router.get("/projects", response_model=List[VideoProject])
def list_projects(
    tenant_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context, tenant_id=tenant_id)
    return get_timeline_service().list_projects(tenant_id)


@router.get("/projects/{project_id}", response_model=VideoProject)
def get_project(
    project_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    proj = get_timeline_service().get_project(project_id)
    if not proj:
        _not_found("project")
    return proj


@router.patch("/projects/{project_id}", response_model=VideoProject)
def update_project(
    project_id: str,
    project: VideoProject,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=project.tenant_id,
        env=project.env,
    )
    if project.id != project_id:
        raise HTTPException(status_code=400, detail="project id mismatch")
    return get_timeline_service().update_project(project)


# Sequences
@router.post("/projects/{project_id}/sequences", response_model=Sequence)
def create_sequence(
    project_id: str,
    sequence: Sequence,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=sequence.tenant_id,
        env=sequence.env,
    )
    if sequence.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id mismatch")
    return get_timeline_service().create_sequence(sequence)


@router.get("/projects/{project_id}/sequences", response_model=List[Sequence])
def list_sequences(
    project_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    return get_timeline_service().list_sequences_for_project(project_id)


@router.get("/sequences/{sequence_id}", response_model=Sequence)
def get_sequence(
    sequence_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    seq = get_timeline_service().get_sequence(sequence_id)
    if not seq:
        _not_found("sequence")
    return seq


@router.patch("/sequences/{sequence_id}", response_model=Sequence)
def update_sequence(
    sequence_id: str,
    sequence: Sequence,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=sequence.tenant_id,
        env=sequence.env,
    )
    if sequence.id != sequence_id:
        raise HTTPException(status_code=400, detail="sequence id mismatch")
    return get_timeline_service().update_sequence(sequence)


# Tracks
@router.post("/sequences/{sequence_id}/tracks", response_model=Track)
def create_track(
    sequence_id: str,
    track: Track,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=track.tenant_id,
        env=track.env,
    )
    if track.sequence_id != sequence_id:
        raise HTTPException(status_code=400, detail="sequence_id mismatch")
    return get_timeline_service().create_track(track)


@router.get("/sequences/{sequence_id}/tracks", response_model=List[Track])
def list_tracks(
    sequence_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    return get_timeline_service().list_tracks_for_sequence(sequence_id)


@router.get("/tracks/{track_id}", response_model=Track)
def get_track(
    track_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    track = get_timeline_service().get_track(track_id)
    if not track:
        _not_found("track")
    return track


@router.patch("/tracks/{track_id}", response_model=Track)
def update_track(
    track_id: str,
    track: Track,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=track.tenant_id,
        env=track.env,
    )
    if track.id != track_id:
        raise HTTPException(status_code=400, detail="track id mismatch")
    return get_timeline_service().update_track(track)


# Clips
@router.post("/tracks/{track_id}/clips", response_model=Clip)
def create_clip(
    track_id: str,
    clip: Clip,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=clip.tenant_id,
        env=clip.env,
    )
    if clip.track_id != track_id:
        raise HTTPException(status_code=400, detail="track_id mismatch")
    return get_timeline_service().create_clip(clip)


@router.get("/tracks/{track_id}/clips", response_model=List[Clip])
def list_clips(
    track_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    return get_timeline_service().list_clips_for_track(track_id)


@router.get("/clips/{clip_id}", response_model=Clip)
def get_clip(
    clip_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    clip = get_timeline_service().get_clip(clip_id)
    if not clip:
        _not_found("clip")
    return clip


@router.patch("/clips/{clip_id}", response_model=Clip)
def update_clip(
    clip_id: str,
    clip: Clip,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=clip.tenant_id,
        env=clip.env,
    )
    if clip.id != clip_id:
        raise HTTPException(status_code=400, detail="clip id mismatch")
    return get_timeline_service().update_clip(clip)


@router.delete("/clips/{clip_id}")
def delete_clip(
    clip_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    get_timeline_service().delete_clip(clip_id)
    return {"status": "deleted", "id": clip_id}


# Transitions
@router.post("/sequences/{sequence_id}/transitions", response_model=Transition)
def create_transition(
    sequence_id: str,
    transition: Transition,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=transition.tenant_id,
        env=transition.env,
    )
    if transition.sequence_id != sequence_id:
        raise HTTPException(status_code=400, detail="sequence_id mismatch")
    return get_timeline_service().create_transition(transition)


@router.get("/sequences/{sequence_id}/transitions", response_model=List[Transition])
def list_transitions(
    sequence_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    return get_timeline_service().list_transitions_for_sequence(sequence_id)


@router.patch("/transitions/{transition_id}", response_model=Transition)
def update_transition(
    transition_id: str,
    transition: Transition,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=transition.tenant_id,
        env=transition.env,
    )
    if transition.id != transition_id:
        raise HTTPException(status_code=400, detail="transition id mismatch")
    return get_timeline_service().update_transition(transition)


@router.delete("/transitions/{transition_id}")
def delete_transition(
    transition_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    get_timeline_service().delete_transition(transition_id)
    return {"status": "deleted", "id": transition_id}


# Filter stacks
@router.post("/filter-stacks/{target_type}/{target_id}", response_model=FilterStack)
def create_filter_stack(
    target_type: str,
    target_id: str,
    stack: FilterStack,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=stack.tenant_id,
        env=stack.env,
    )
    if stack.target_type != target_type or stack.target_id != target_id:
        raise HTTPException(status_code=400, detail="target mismatch")
    return get_timeline_service().create_filter_stack(stack)


@router.get("/filter-stacks/{target_type}/{target_id}", response_model=FilterStack)
def get_filter_stack_for_target(
    target_type: str,
    target_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    stack = get_timeline_service().get_filter_stack_for_target(target_type, target_id)
    if not stack:
        _not_found("filter_stack")
    return stack


@router.patch("/filter-stacks/{stack_id}", response_model=FilterStack)
def update_filter_stack(
    stack_id: str,
    stack: FilterStack,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=stack.tenant_id,
        env=stack.env,
    )
    if stack.id != stack_id:
        raise HTTPException(status_code=400, detail="stack id mismatch")
    return get_timeline_service().update_filter_stack(stack)


@router.delete("/filter-stacks/{stack_id}")
def delete_filter_stack(
    stack_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    get_timeline_service().delete_filter_stack(stack_id)
    return {"status": "deleted", "id": stack_id}


# Automation
@router.post("/automation", response_model=ParameterAutomation)
def create_automation(
    automation: ParameterAutomation,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=automation.tenant_id,
        env=automation.env,
    )
    return get_timeline_service().create_automation(automation)


@router.get("/automation/{automation_id}", response_model=ParameterAutomation)
def get_automation(
    automation_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    res = get_timeline_service().get_automation(automation_id)
    if not res:
        _not_found("automation")
    return res


@router.get("/automation", response_model=list[ParameterAutomation])
def list_automation(
    target_type: str,
    target_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    return get_timeline_service().list_automation(target_type, target_id)


@router.patch("/automation/{automation_id}", response_model=ParameterAutomation)
def update_automation(
    automation_id: str,
    automation: ParameterAutomation,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=automation.tenant_id,
        env=automation.env,
    )
    if automation.id != automation_id:
        raise HTTPException(status_code=400, detail="automation id mismatch")
    return get_timeline_service().update_automation(automation)


@router.delete("/automation/{automation_id}")
def delete_automation(
    automation_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    get_timeline_service().delete_automation(automation_id)
    return {"status": "deleted", "id": automation_id}


# T01.2 Edit Ops Routes
@router.post("/clips/{clip_id}/trim", response_model=Clip)
def trim_clip(
    clip_id: str,
    new_in_ms: float = Body(...),
    new_out_ms: float = Body(...),
    ripple: bool = Body(False),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    try:
        return get_timeline_service().trim_clip(clip_id, new_in_ms, new_out_ms, ripple)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clips/{clip_id}/split", response_model=Clip)
def split_clip(
    clip_id: str,
    split_time_ms: float = Body(...),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    try:
        return get_timeline_service().split_clip(clip_id, split_time_ms)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clips/{clip_id}/move", response_model=Clip)
def move_clip(
    clip_id: str,
    new_start_ms: float = Body(...),
    track_id: Optional[str] = Body(None),
    ripple: bool = Body(False),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(request_context, auth_context)
    try:
        return get_timeline_service().move_clip(clip_id, new_start_ms, track_id, ripple)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# T01.4 Multicam
@router.post("/projects/{project_id}/multicam/promote", response_model=Sequence)
def promote_multicam(
    project_id: str,
    name: str = Body(...),
    result: dict = Body(...),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=result.get("tenant_id"),
        env=result.get("env"),
    )
    try:
        return get_timeline_service().promote_multicam_to_sequence(project_id, name, result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# T01.5 Assist
@router.post("/sequences/{sequence_id}/assist/ingest", response_model=Track)
def ingest_assist(
    sequence_id: str,
    result: dict = Body(...),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=result.get("tenant_id"),
        env=result.get("env"),
    )
    try:
        return get_timeline_service().ingest_assist_highlights(sequence_id, result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# T01.5 Focus
@router.post("/clips/{clip_id}/focus/apply", response_model=List[ParameterAutomation])
def apply_focus(
    clip_id: str,
    result: dict = Body(...),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _enforce_timeline_guard(
        request_context,
        auth_context,
        tenant_id=result.get("tenant_id"),
        env=result.get("env"),
    )
    try:
        return get_timeline_service().apply_focus_automation(clip_id, result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
