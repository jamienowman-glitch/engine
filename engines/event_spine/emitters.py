"""Event emitters for unified event spine (Agent A - A-5).

Provides canonical emitters for all domains:
- safety decisions (GateChain)
- RL / RLHA telemetry
- tuning / optimization logs
- budget / usage tracking
- strategy lock snapshots
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.event_spine.validation_service import EventSpineServiceWithValidation

logger = logging.getLogger(__name__)


class SafetyEmitter:
    """Emits safety decision events (GateChain outcomes) to event spine.
    
    Every safety check result persists with full justification/metadata.
    """
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_safety_decision(
        self,
        run_id: str,
        decision: str,  # "allow" | "block" | "review" | "error"
        gate_name: str,
        justification: Dict[str, Any],
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[str]:
        """Emit safety decision event (never dropped)."""
        payload = {
            "decision": decision,
            "gate_name": gate_name,
            "justification": justification,
        }
        
        return self._spine.emit(
            event_type="safety",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )


class RLEmitter:
    """Emits RL / RLHA telemetry to event spine (training feedback)."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_rl_telemetry(
        self,
        run_id: str,
        signal_type: str,  # "reward" | "penalty" | "feedback" | ...
        value: float,
        source_node: Optional[str] = None,
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Emit RL telemetry (for training/feedback loops)."""
        payload = {
            "signal_type": signal_type,
            "value": value,
            "source_node": source_node,
        }
        if metadata:
            payload["metadata"] = metadata
        
        return self._spine.emit(
            event_type="rl",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )
    
    def emit_rlha_telemetry(
        self,
        run_id: str,
        signal_type: str,
        value: float,
        source_node: Optional[str] = None,
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Emit RLHA telemetry (human-aligned feedback)."""
        payload = {
            "signal_type": signal_type,
            "value": value,
            "source_node": source_node,
        }
        if metadata:
            payload["metadata"] = metadata
        
        return self._spine.emit(
            event_type="rlha",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )


class TuningEmitter:
    """Emits tuning / optimization logs to event spine."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_tuning_log(
        self,
        run_id: str,
        tuning_type: str,  # "parameter_sweep" | "experiment" | "ablation" | ...
        metrics: Dict[str, Any],
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Emit tuning/optimization log."""
        payload = {
            "tuning_type": tuning_type,
            "metrics": metrics,
        }
        if parameters:
            payload["parameters"] = parameters
        
        return self._spine.emit(
            event_type="tuning",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )


class BudgetEmitter:
    """Emits budget / usage tracking to event spine (append-only ledger)."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_budget_usage(
        self,
        run_id: str,
        resource_type: str,  # "tokens" | "calls" | "time" | ...
        amount: float,
        unit: str,  # "tokens" | "count" | "seconds" | ...
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Emit budget usage for enforcement and tracking."""
        payload = {
            "resource_type": resource_type,
            "amount": amount,
            "unit": unit,
        }
        if metadata:
            payload["metadata"] = metadata
        
        return self._spine.emit(
            event_type="budget",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )


class StrategyLockEmitter:
    """Emits strategy lock snapshots to event spine."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_strategy_lock(
        self,
        run_id: str,
        lock_name: str,
        is_locked: bool,
        reason: Optional[str] = None,
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Emit strategy lock state change."""
        payload = {
            "lock_name": lock_name,
            "is_locked": is_locked,
            "reason": reason,
        }
        if metadata:
            payload["metadata"] = metadata
        
        return self._spine.emit(
            event_type="strategy_lock",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )


class AuditEmitter:
    """Emits audit events to event spine (append-only audit trail)."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_audit(
        self,
        run_id: str,
        action: str,
        resource: str,
        outcome: str,  # "success" | "failure" | "denied" | ...
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Emit audit event (queryable via event spine)."""
        payload = {
            "action": action,
            "resource": resource,
            "outcome": outcome,
        }
        if metadata:
            payload["metadata"] = metadata
        
        return self._spine.emit(
            event_type="audit",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload=payload,
        )


class AnalyticsEmitter:
    """Emits analytics events to event spine (cross-domain analytics)."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._spine = EventSpineServiceWithValidation(context)
    
    def emit_analytics(
        self,
        run_id: str,
        event_name: str,
        properties: Dict[str, Any],
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[str]:
        """Emit analytics event (ingested by analytics pipeline)."""
        return self._spine.emit(
            event_type="analytics",
            source="agent",
            run_id=run_id,
            step_id=step_id,
            parent_event_id=parent_event_id,
            trace_id=trace_id,
            payload={"event_name": event_name, "properties": properties},
        )
