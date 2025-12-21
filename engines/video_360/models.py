from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _uuid() -> str:
    return uuid.uuid4().hex


class VirtualCameraKeyframe(BaseModel):
    time_ms: int
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    fov: float = 90.0
    interpolation: Literal["linear", "bezier", "hold"] = "linear"


class VirtualCameraPath(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str  # 360 source asset
    name: str = "New Camera Path"
    keyframes: List[VirtualCameraKeyframe] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class Render360Request(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    path_id: Optional[str] = None
    # Inline path option for quick renders
    path: Optional[VirtualCameraPath] = None
    render_profile: str = "preview_720p_fast"  # Reuse standard profiles
    
    # 360 specific render output settings
    output_projection: str = "flat"  # v360 output type
    width: Optional[int] = None
    height: Optional[int] = None


class Render360Response(BaseModel):
    asset_id: str
    artifact_id: str
    uri: str
    meta: Dict[str, Any]
