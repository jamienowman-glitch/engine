from __future__ import annotations
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# Presets defined as Literal for type safety, though we might want to load dynamic list later.
# For now, hardcode P1 types.
FxPresetId = Literal[
    "clean_hit", 
    "lofi_crunch", 
    "bright_snare", 
    "warm_pad", 
    "vocal_presence",
    "bass_glue",
    "sub_rumble",
    "tape_warmth",
    "wide_chorus",
    "transient_snap",
    "saturation_sizzle",
    "delay_dream",
    "wide_spread",
    "ambient_tail"
]

class FxChainRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    
    # Input
    asset_id: Optional[str] = None
    artifact_id: Optional[str] = None
    # If both missing, error. If both present, artifact takes precedence?
    
    preset_id: FxPresetId
    dry_wet: float = 1.0 # 0.0 to 1.0
    
    # Overrides (advanced usage)
    params_override: Optional[Dict[str, Any]] = None
    
    # Output Control
    output_format: str = "wav" # wav, mp3

class FxChainResult(BaseModel):
    artifact_id: str
    uri: str
    preset_id: str
    params_applied: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)
