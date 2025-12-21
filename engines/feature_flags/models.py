from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class FeatureFlags(BaseModel):
    """
    Control rails and visibility for a specific tenant/env.
    """

    tenant_id: str
    env: str
    ws_enabled: bool = Field(default=False, description="Enable WebSocket transport")
    sse_enabled: bool = Field(default=False, description="Enable SSE transport")
    gesture_logging: bool = Field(default=False, description="Store gesture events")
    replay_mode: str = Field(
        default="off", description="off | keyframe | stream"
    )
    visibility_mode: str = Field(
        default="private", description="private | team | public"
    )

    class Config:
        extra = "ignore"
