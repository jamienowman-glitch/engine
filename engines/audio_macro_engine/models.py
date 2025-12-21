from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class MacroNode(BaseModel):
    type: str # reverse, reverb, distortion, delay, chorus, limiter
    params: Dict[str, Union[float, int, str]] = Field(default_factory=dict)

class MacroDefinition(BaseModel):
    id: str
    nodes: List[MacroNode]
    meta: Dict[str, Any] = Field(default_factory=dict)

class MacroRequest(BaseModel):
    tenant_id: str
    env: str
    
    artifact_id: str
    macro_id: str
    
    # Optional parameter overrides
    # key format: "node_index.param_name" or just "param_name" if unique?
    # For V1: specific "knobs" mapped in definition?
    # Let's support simple param overrides dict for now.
    knob_overrides: Dict[str, Any] = Field(default_factory=dict)
    
    output_format: str = "wav"

class MacroResult(BaseModel):
    artifact_id: str
    uri: str
    duration_ms: float
    meta: Dict[str, Any] = Field(default_factory=dict)
