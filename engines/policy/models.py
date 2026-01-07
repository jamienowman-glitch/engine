from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Requirements(BaseModel):
    firearms: bool = False
    licenses: List[str] = Field(default_factory=list) # e.g. ["finance", "hr"]

class PolicyAttachment(BaseModel):
    # Mapping: scope_identifier -> Requirements
    # scope_identifier format: "tool_id.scope_name"
    scopes: Dict[str, Requirements] = Field(default_factory=dict)
