"""Shared orchestration schemas for agent runtimes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentStepRequest:
    agent_id: str
    input: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    episode_id: Optional[str] = None


@dataclass
class AgentStepResult:
    output: Dict[str, Any]
    traces: Dict[str, Any] = field(default_factory=dict)
    model_calls: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowRequest:
    workflow_id: str
    graph_spec: Dict[str, Any]
    inputs: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    episode_id: Optional[str] = None


@dataclass
class WorkflowResult:
    output: Dict[str, Any]
    traces: Dict[str, Any] = field(default_factory=dict)
    model_calls: List[Dict[str, Any]] = field(default_factory=list)
