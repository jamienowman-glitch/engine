from typing import List, Optional

from fastapi import APIRouter, HTTPException

from engines.video_360.models import (
    Render360Request,
    Render360Response,
    VirtualCameraPath,
)
from engines.video_360.service import get_video_360_service

router = APIRouter(prefix="/video/360", tags=["video_360"])


@router.post("/camera-paths", response_model=VirtualCameraPath)
def create_path(path: VirtualCameraPath):
    service = get_video_360_service()
    return service.create_path(path)


@router.get("/camera-paths/{path_id}", response_model=VirtualCameraPath)
def get_path(path_id: str):
    service = get_video_360_service()
    path = service.get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
    return path


@router.get("/camera-paths", response_model=List[VirtualCameraPath])
def list_paths(tenant_id: str, asset_id: Optional[str] = None):
    service = get_video_360_service()
    return service.list_paths(tenant_id, asset_id)


@router.post("/render", response_model=Render360Response)
def render_360(req: Render360Request):
    service = get_video_360_service()
    try:
        return service.render_360_to_flat(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch-all for ffmpeg errors or other issues
        raise HTTPException(status_code=500, detail=str(e))
