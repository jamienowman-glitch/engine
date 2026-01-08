from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# --- Layer 1: Portable MCP Package ---
# Safe for public distribution. No policy, no routing, no PII.

class ToolDefinition(BaseModel):
    id: str
    name: str
    summary: str
    metrics: List[MetricDefinition] = Field(default_factory=list)

class MetricDefinition(BaseModel):
    name: str
    description: str
    unit: str # count, ms, currency

class PortableMCPPackage(BaseModel):
    id: str # e.g. "com.acme.echo"
    version: str # "1.0.0"
    name: str
    description: str
    tools: List[ToolDefinition]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
# --- Layer 2: Northstar Activation Overlay ---
# Internal context. Policy, Routing, Telemetry.

class PolicyConfig(BaseModel):
    firearms: bool = False
    required_licenses: List[str] = Field(default_factory=list) # e.g. ["finance", "hr"]

class UTMConfig(BaseModel):
    platform: str
    content_type: str

class BudgetConfig(BaseModel):
    cost_per_call: float = 0.0
    free_tier_daily_cap: int = 100

class ScopeOverlay(BaseModel):
    policy: Optional[PolicyConfig] = None
    utm_config: Optional[UTMConfig] = None
    budget_config: Optional[BudgetConfig] = None
    # Future: routing_guardrails, telemetry_sampling

class ToolOverlay(BaseModel):
    scopes: Dict[str, ScopeOverlay] = Field(default_factory=dict)

class NorthstarActivationOverlay(BaseModel):
    package_id: str
    package_version: str # e.g. ">=1.0.0" or specific "1.2.3"
    
    # Map tool_id -> content
    tools: Dict[str, ToolOverlay] = Field(default_factory=dict)
    
    enabled: bool = True
