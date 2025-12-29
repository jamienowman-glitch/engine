from __future__ import annotations

from fastapi import APIRouter, HTTPException

from engines.video_presets.models import FilterPreset, MotionPreset
from engines.video_presets.service import get_preset_service

router = APIRouter(prefix="/video/presets", tags=["video_presets"])


@router.post("/filters", response_model=FilterPreset)
def create_filter_preset(preset: FilterPreset):
    return get_preset_service().create_filter_preset(preset)


@router.get("/filters", response_model=list[FilterPreset])
def list_filter_presets(tenant_id: str, env: str | None = None, tag: str | None = None):
    return get_preset_service().list_filter_presets(tenant_id=tenant_id, env=env, tag=tag)


@router.get("/filters/{preset_id}", response_model=FilterPreset)
def get_filter_preset(preset_id: str):
    preset = get_preset_service().get_filter_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="filter preset not found")
    return preset


@router.delete("/filters/{preset_id}")
def delete_filter_preset(preset_id: str):
    get_preset_service().delete_filter_preset(preset_id)
    return {"status": "deleted", "id": preset_id}


@router.post("/motion", response_model=MotionPreset)
def create_motion_preset(preset: MotionPreset):
    return get_preset_service().create_motion_preset(preset)


@router.get("/motion", response_model=list[MotionPreset])
def list_motion_presets(tenant_id: str, env: str | None = None, tag: str | None = None):
    return get_preset_service().list_motion_presets(tenant_id=tenant_id, env=env, tag=tag)


@router.get("/motion/{preset_id}", response_model=MotionPreset)
def get_motion_preset(preset_id: str):
    preset = get_preset_service().get_motion_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="motion preset not found")
    return preset


@router.delete("/motion/{preset_id}")
def delete_motion_preset(preset_id: str):
    get_preset_service().delete_motion_preset(preset_id)
    return {"status": "deleted", "id": preset_id}
