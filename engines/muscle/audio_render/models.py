from __future__ import annotations
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from engines.audio_timeline.models import AudioSequence

class RenderRequest(BaseModel):
    sequence: AudioSequence
    output_format: str = "wav" # wav, mp3
    
    # Options
    loudnorm_target_lufs: Optional[float] = None # -14.0 etc.
    stems_export: bool = False # If true, export per-track/bus stems
    mix_preset_id: Optional[str] = None # e.g. "default_mix"
    export_preset: Literal["default", "podcast", "music", "voiceover"] = "default"


class RenderResult(BaseModel):
    artifact_id: str
    uri: str
    duration_ms: float
    meta: Dict[str, Any] = Field(default_factory=dict)
