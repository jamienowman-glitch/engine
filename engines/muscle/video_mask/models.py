from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class MaskPrompt(BaseModel):
    prompt_type: Literal["point", "box", "face_region"]
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    region: Optional[Literal["skin", "teeth", "eyes", "lips", "background"]] = None


class MaskRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    source_asset_id: Optional[str] = None
    artifact_id: Optional[str] = None
    prompt: MaskPrompt
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    quality: Literal["fast", "balanced", "high"] = "balanced"


class MaskResult(BaseModel):
    artifact_id: str
    uri: str
    meta: Dict[str, Any] = Field(default_factory=dict)
