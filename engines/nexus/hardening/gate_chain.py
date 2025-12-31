from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from fastapi import HTTPException

from engines.budget.repository import BudgetPolicyRepository, get_budget_policy_repo
from engines.budget.service import BudgetService, get_budget_service
from engines.common.identity import RequestContext
from engines.firearms.service import DANGEROUS_ACTIONS, FirearmsService, get_firearms_service
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.kpi.service import KpiService, get_kpi_service
from engines.logging.audit import emit_audit_event
from engines.strategy_lock.service import StrategyLockService, get_strategy_lock_service
from engines.temperature.service import TemperatureService, get_temperature_service
from engines.realtime.contracts import (
    EventIds,
    StreamEvent,
    RoutingKeys,
    ActorType,
    EventPriority,
    PersistPolicy,
    EventMeta,
)
from engines.realtime.timeline import get_timeline_store
from engines.logging.events.contract import EventSeverity


class GateChain:
    def __init__(
        self,
        kill_switch_service: Optional[KillSwitchService] = None,
        firearms_service: Optional[FirearmsService] = None,
        strategy_lock_service: Optional[StrategyLockService] = None,
        budget_service: Optional[BudgetService] = None,
        kpi_service: Optional[KpiService] = None,
        temperature_service: Optional[TemperatureService] = None,
        budget_policy_repo: Optional[BudgetPolicyRepository] = None,
        audit_logger: Callable = emit_audit_event,
    ):
        self.kill_switch = kill_switch_service or get_kill_switch_service()
        self.firearms = firearms_service or get_firearms_service()
        self.strategy_lock = strategy_lock_service or get_strategy_lock_service()
        self.budget_service = budget_service or get_budget_service()
        self.kpi_service = kpi_service or get_kpi_service()
        self.temperature_service = temperature_service or get_temperature_service()
        self._budget_policy_repo = budget_policy_repo or get_budget_policy_repo()
        self._audit_logger = audit_logger

    def run(
        self,
        ctx: RequestContext,
        action: str,
        surface: Optional[str],
        subject_type: Optional[str],
        subject_id: Optional[str] = None,
        *,
        skip_metrics: bool = False,
    ) -> None:
        surface_key = surface or "nexus"
        gate_blocked = None
        reason_code = None
        
        try:
            self.kill_switch.ensure_action_allowed(ctx, action)
        except HTTPException as exc:
            gate_blocked = "kill_switch"
            reason_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
            self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked)
            raise

        try:
            if action in DANGEROUS_ACTIONS:
                self.firearms.require_licence_or_raise(ctx, subject_type or "unknown", subject_id or action, action)
        except HTTPException as exc:
            gate_blocked = "firearms"
            reason_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
            self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked)
            raise

        try:
            self.strategy_lock.require_strategy_lock_or_raise(ctx, surface_key, action)
        except HTTPException as exc:
            gate_blocked = "strategy_lock"
            reason_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
            self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked)
            raise

        if not skip_metrics:
            try:
                self._enforce_budget(ctx, surface_key, action)
            except HTTPException as exc:
                gate_blocked = "budget"
                reason_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
                self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked)
                raise
            
            try:
                self._enforce_kpi(ctx, surface_key, action)
            except HTTPException as exc:
                gate_blocked = "kpi"
                reason_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
                self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked)
                raise
            
            try:
                self._enforce_temperature(ctx, surface_key, action)
            except HTTPException as exc:
                gate_blocked = "temperature"
                reason_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
                self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked)
                raise

        # All gates passed - emit SAFETY_DECISION PASS
        self._emit_safety_decision(ctx, action, subject_type, subject_id, "PASS", "passed", "all_gates")
        self._emit_audit(ctx, action, surface_key, subject_type, subject_id, skip_metrics)

    def _emit_safety_decision(
        self,
        ctx: RequestContext,
        action: str,
        subject_type: Optional[str],
        subject_id: Optional[str],
        result: str,  # PASS or BLOCK
        reason: str,
        gate: str,
    ) -> None:
        """Emit a SAFETY_DECISION event to the timeline."""
        if not subject_id:
            return  # Cannot emit to timeline without a stream ID
        
        # Determine the stream_id based on subject_type
        stream_id = subject_id  # For chat: thread_id, for canvas: canvas_id
        
        # Build the SAFETY_DECISION event
        safety_event = StreamEvent(
            type="SAFETY_DECISION",
            routing=RoutingKeys(
                tenant_id=ctx.tenant_id,
                mode=ctx.mode,
                env=ctx.env,
                project_id=ctx.project_id,
                surface_id=ctx.surface_id,
                thread_id=stream_id if subject_type == "thread" else None,
                canvas_id=stream_id if subject_type == "canvas" else None,
                actor_id="system",
                actor_type=ActorType.SYSTEM,
            ),
            ids=EventIds(
                request_id=ctx.request_id,
                run_id=stream_id,
                step_id="safety_decision",
            ),
            trace_id=ctx.request_id,
            data={
                "action": action,
                "result": result,
                "reason": reason,
                "gate": gate,
            },
            meta=EventMeta(
                priority=EventPriority.TRUTH,
                persist=PersistPolicy.ALWAYS,
                severity=EventSeverity.WARNING if result == "BLOCK" else EventSeverity.INFO,
            ),
        )
        
        try:
            timeline = get_timeline_store()
            timeline.append(stream_id, safety_event, ctx)
        except Exception:
            # Silently fail if timeline is unavailable; don't block user request
            pass
        
        # Also emit to audit log
        self._audit_logger(
            ctx,
            action="safety_decision",
            surface="gate_chain",
            metadata={
                "gate_action": action,
                "gate": gate,
                "result": result,
                "reason": reason,
                "subject_type": subject_type,
                "subject_id": subject_id,
            },
        )

    def _enforce_budget(self, ctx: RequestContext, surface: str, action: str) -> None:
        policy = self._budget_policy_repo.get_policy(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface=surface,
            mode=ctx.mode,
            app=ctx.app_id,
        )
        if policy is None:
            raise HTTPException(
                status_code=403,
                detail={"error": "budget_threshold_missing", "surface": surface},
            )

        summary_surface = policy.surface
        try:
            summary = self.budget_service.summary(ctx, surface=summary_surface)
        except Exception as exc:
            raise HTTPException(status_code=403, detail={"error": "budget_unavailable", "reason": str(exc)})

        total_cost = summary.get("total_cost")
        try:
            total = Decimal(str(total_cost))
        except (InvalidOperation, TypeError):
            total = Decimal("0")

        if total > policy.threshold:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "budget_threshold_exceeded",
                    "surface": surface,
                    "policy_surface": policy.surface,
                    "policy_mode": policy.mode,
                    "policy_app": policy.app,
                    "total_cost": float(total),
                    "threshold": float(policy.threshold),
                    "action": action,
                },
            )

    def _enforce_kpi(self, ctx: RequestContext, surface: str, action: str) -> None:
        try:
            corridors = self.kpi_service.list_corridors(ctx, surface=surface)
        except Exception as exc:
            raise HTTPException(status_code=403, detail={"error": "kpi_unavailable", "reason": str(exc)})

        if not corridors:
            if os.environ.get("GATECHAIN_ALLOW_MISSING") == "1":
                return
            raise HTTPException(
                status_code=403,
                detail={"error": "kpi_threshold_missing", "surface": surface, "action": action},
            )

    def _enforce_temperature(self, ctx: RequestContext, surface: str, action: str) -> None:
        try:
            snapshot = self.temperature_service.compute_temperature(ctx, surface)
        except Exception as exc:
            raise HTTPException(status_code=403, detail={"error": "temperature_unavailable", "reason": str(exc)})

        if getattr(snapshot, "floors_breached", None) or getattr(snapshot, "ceilings_breached", None):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "temperature_breach",
                    "surface": surface,
                    "floors": getattr(snapshot, "floors_breached", []),
                    "ceilings": getattr(snapshot, "ceilings_breached", []),
                    "action": action,
                },
            )

    def _emit_audit(
        self,
        ctx: RequestContext,
        action: str,
        surface: str,
        subject_type: Optional[str],
        subject_id: Optional[str],
        skip_metrics: bool,
    ) -> None:
        metadata = {
            "action": action,
            "surface": surface,
            "subject_type": subject_type or "unknown",
        }
        if subject_id:
            metadata["subject_id"] = subject_id
        if skip_metrics:
            metadata["persist"] = False
        self._audit_logger(
            ctx,
            action="gate_chain.check",
            surface="gate_chain",
            metadata=metadata,
        )


_gate_chain: Optional[GateChain] = None


def get_gate_chain() -> GateChain:
    global _gate_chain
    if _gate_chain is None:
        _gate_chain = GateChain()
    return _gate_chain


def set_gate_chain(chain: GateChain) -> None:
    global _gate_chain
    _gate_chain = chain
