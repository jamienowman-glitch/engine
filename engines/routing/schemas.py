"""Shared routing schemas for Rootsmanuva and Selecta Loop."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RoutingMetricWeight(BaseModel):
    key: str
    weight: float
    direction: Optional[Literal["higher_is_better", "lower_is_better"]] = None
    required: Optional[bool] = None


class RoutingFallbackConfig(BaseModel):
    use_free_credits_first: Optional[bool] = None
    max_cost_usd_per_day: Optional[float] = None
    max_latency_ms_p95: Optional[float] = None
    allow_missing_metrics: bool = False
    missing_metric_penalty: Optional[float] = None


class RoutingProfile(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    selector_agent_card_id: Optional[str] = None
    metrics: List[RoutingMetricWeight] = Field(default_factory=list)
    fallback: Optional[RoutingFallbackConfig] = None
    scope: Optional[Dict[str, str]] = None


class ModelMetricsSnapshot(BaseModel):
    candidate_id: str
    vendor: str
    model_id: str
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    tenant_id: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None


class CandidateOption(BaseModel):
    snapshot: ModelMetricsSnapshot
    hard_constraints: Optional[Dict[str, Any]] = None


class RoutingDecision(BaseModel):
    routing_profile_id: str
    requested_at: datetime
    tenant_id: str
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    candidates: List[CandidateOption]
    selected_candidate_id: Optional[str] = None
    ranking: List[str] = Field(default_factory=list)
    score_by_candidate: Dict[str, float] = Field(default_factory=dict)
    reasons: Optional[List[str]] = None
    flags: Optional[List[str]] = None


class RoutingContext(BaseModel):
    tenant_id: str
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    episode_id: Optional[str] = None
    request_kind: str
    timestamp: datetime


class ProposedRoutingProfileUpdate(BaseModel):
    profile_id: str
    current_profile: RoutingProfile
    suggested_profile: RoutingProfile
    summary: str
    source: Optional[Literal["ceo_agent", "data_scientist_agent", "coder_agent", "mixed", "other"]] = None
    confidence: Optional[float] = None


class MetricDefinition(BaseModel):
    key: str
    label: str
    description: str
    unit: Optional[str] = None
    direction: Literal["higher_is_better", "lower_is_better", "neutral"] = "neutral"
    category: Optional[str] = None
    visible_in_ui: bool = True
