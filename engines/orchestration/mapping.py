"""Card-to-runtime mapping and trace normalization helpers."""
from __future__ import annotations

from typing import Any, Dict

from engines.orchestration.schemas import AgentStepRequest, WorkflowRequest


def card_to_runtime_config(card: Dict[str, Any]) -> Dict[str, Any]:
    """Translate card metadata into runtime config; placeholder mapping."""
    # TODO MISSING_CANONICAL_NAME for card fields if schema evolves
    return {
        "models": card.get("models"),
        "tools": card.get("tools"),
        "safety": card.get("safety"),
        "vendor": card.get("vendor"),
        "cost_tier": card.get("cost_tier"),
    }


def build_agent_step_request(card: Dict[str, Any], payload: Dict[str, Any]) -> AgentStepRequest:
    return AgentStepRequest(
        agent_id=card.get("agent_id", ""),
        input=payload,
        context=card_to_runtime_config(card),
        episode_id=payload.get("episode_id"),
    )


def build_workflow_request(card: Dict[str, Any], payload: Dict[str, Any]) -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id=card.get("workflow_id", ""),
        graph_spec=card.get("graph_spec", {}),
        inputs=payload,
        context=card_to_runtime_config(card),
        episode_id=payload.get("episode_id"),
    )


def normalize_traces(native_trace: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder normalization from runtime-specific trace to standard form."""
    return {"raw": native_trace}
