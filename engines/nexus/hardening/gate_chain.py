from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from fastapi import HTTPException

from engines.budget.repository import BudgetPolicyRepository, get_budget_policy_repo
from engines.budget.service import BudgetService, get_budget_service
from engines.common.identity import RequestContext
from engines.common.error_envelope import error_response
from engines.common.surface_normalizer import normalize_surface_id
from engines.firearms.service import FirearmsService, get_firearms_service
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.kpi.service import KpiService, get_kpi_service
from engines.logging.audit import emit_audit_event
from engines.logging.audit import emit_audit_event
from engines.strategy_lock.service import StrategyLockService, get_strategy_lock_service
from engines.strategy_lock.resolution import resolve_strategy_lock
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
        budget_check: Optional[Dict[str, Any]] = None, # {cost, cap, tool_id}
    ) -> None:
        surface_key = surface or "nexus"
        gate_blocked = None
        reason_code = None
        
        # Worker 7: Tool Budget Check (W-07)
        if budget_check:
             try:
                 self._enforce_tool_budget(ctx, action, budget_check)
             except HTTPException as exc:
                 gate_blocked = "budget"
                 reason_code, details = self._extract_error_fields(exc)
                 self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
                 raise

        try:
            self.kill_switch.ensure_action_allowed(ctx, action)
        except HTTPException as exc:
            gate_blocked = "kill_switch"
            reason_code, details = self._extract_error_fields(exc)
            self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
            raise

        try:
            # Worker 7: New Firearms Binding Check
            # Action logic: If "action" is bound to a firearm -> 
            # 1. Check Grant (throws 403 if missing)
            # 2. Return decision.strategy_lock_required
            
            firearms_decision = self.firearms.check_access(ctx, action)
            if not firearms_decision.allowed:
                # Block immediate with new contract
                error_response(
                    code="firearms.license_required",
                    message="Firearm license required for this action",
                    status_code=403,
                    gate="firearms",
                    action_name=action,
                    details={
                        "required_license_types": firearms_decision.required_license_types,
                        "action": action,
                        "subject_type": subject_type or "unknown",
                        "subject_id": subject_id or "unknown",
                    },
                )
            
        except HTTPException as exc:
            gate_blocked = "firearms"
            reason_code, details = self._extract_error_fields(exc)
            self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
            raise

        try:
            # self.strategy_lock.require_strategy_lock_or_raise(ctx, surface_key, action)
            # Worker 6: Use new resolution logic
            decision = resolve_strategy_lock(ctx, surface_key, action, subject_type, subject_id)
            
            if not decision.allowed:
                details = {
                    "lock_scope": {"context": surface_key},
                    "action": action,
                }
                if decision.lock_id:
                    details["lock_id"] = decision.lock_id
                if decision.three_wise_verdict:
                    details["three_wise_verdict"] = decision.three_wise_verdict
                error_response(
                    code="strategy_lock.approval_required",
                    message="Strategy lock approval required before execution",
                    status_code=403,
                    gate="strategy_lock",
                    action_name=action,
                    resource_kind="strategy_lock",
                    details=details,
                )
                 
        except HTTPException as exc:
            gate_blocked = "strategy_lock"
            reason_code, details = self._extract_error_fields(exc)
            self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
            raise

        if not skip_metrics:
            try:
                self._enforce_budget(ctx, surface_key, action)
            except HTTPException as exc:
                gate_blocked = "budget"
                reason_code, details = self._extract_error_fields(exc)
                self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
                raise
            
            try:
                self._enforce_kpi(ctx, surface_key, action)
            except HTTPException as exc:
                gate_blocked = "kpi"
                reason_code, details = self._extract_error_fields(exc)
                self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
                raise
            
            try:
                self._enforce_temperature(ctx, surface_key, action)
            except HTTPException as exc:
                gate_blocked = "temperature"
                reason_code, details = self._extract_error_fields(exc)
                self._emit_safety_decision(ctx, action, subject_type, subject_id, "BLOCK", reason_code, gate_blocked, details=details)
                raise

        # All gates passed - emit SAFETY_DECISION PASS
        self._emit_safety_decision(ctx, action, subject_type, subject_id, "PASS", "passed", "all_gates")
        self._emit_audit(ctx, action, surface_key, subject_type, subject_id, skip_metrics)

    def _extract_error_fields(self, exc: HTTPException) -> tuple[str, Optional[dict]]:
        """Normalize error detail to (code, details) tuple."""
        if isinstance(exc.detail, dict):
            error_block = exc.detail.get("error")
            if isinstance(error_block, dict):
                code = error_block.get("code") or error_block.get("message") or "error"
                details = error_block.get("details") or error_block
                return code, details
            return exc.detail.get("error") or str(exc.detail), exc.detail
        return str(exc.detail), None

    def _emit_safety_decision(
        self,
        ctx: RequestContext,
        action: str,
        subject_type: Optional[str],
        subject_id: Optional[str],
        result: str,  # PASS or BLOCK
        reason: str,
        gate: str,
        details: Optional[dict] = None,
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
                run_id=ctx.run_id or stream_id,
                step_id=ctx.step_id or "safety_decision",
            ),
            trace_id=ctx.trace_id or ctx.request_id,
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
        if details:
            safety_event.data["details"] = details
        
        try:
            timeline = get_timeline_store()
            timeline.append(stream_id, safety_event, ctx)
        except Exception:
            # Silently fail if timeline is unavailable; don't block user request
            pass
        
        # Also emit to audit log
        metadata = {
            "gate_action": action,
            "gate": gate,
            "result": result,
            "reason": reason,
            "subject_type": subject_type,
            "subject_id": subject_id,
        }
        if details:
            metadata["details"] = details
        self._audit_logger(
            ctx,
            action="safety_decision",
            surface="gate_chain",
            metadata=metadata,
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
            error_response(
                code="budget_threshold_missing",
                message=f"No budget policy configured for {surface}",
                status_code=403,
                gate="budget",
                action_name=action,
                details={"surface": surface},
            )

        summary_surface = policy.surface
        try:
            summary = self.budget_service.summary(ctx, surface=summary_surface)
        except Exception as exc:
            error_response(
                code="budget_unavailable",
                message="Budget service unavailable",
                status_code=403,
                gate="budget",
                action_name=action,
                details={"reason": str(exc)},
            )

        total_cost = summary.get("total_cost")
        try:
            total = Decimal(str(total_cost))
        except (InvalidOperation, TypeError):
            total = Decimal("0")

        if total > policy.threshold:
            error_response(
                code="budget_threshold_exceeded",
                message=f"Budget threshold exceeded: ${float(total):.2f} > ${float(policy.threshold):.2f}",
                status_code=403,
                gate="budget",
                action_name=action,
                details={
                    "surface": surface,
                    "policy_surface": policy.surface,
                    "policy_mode": policy.mode,
                    "policy_app": policy.app,
                    "total_cost": float(total),
                    "threshold": float(policy.threshold),
                },
            )

    def _enforce_tool_budget(self, ctx: RequestContext, action: str, check: Dict[str, Any]) -> None:
        """Enforce per-tool budget limits (W-07)."""
        cost = Decimal(str(check.get("cost") or 0))
        cap = Decimal(str(check.get("daily_cap") or 0))
        tool_id = check.get("tool_id")
        
        if cap <= 0:
            return # No cap
            
        # Get current spend
        spend = self.budget_service.get_tool_spend(ctx, tool_id, window_days=1)
        
        if spend + cost > cap:
            error_response(
                code="budget.daily_cap_exceeded",
                message=f"Daily budget cap exceeded for tool {tool_id}",
                status_code=403,
                gate="budget",
                action_name=action,
                details={
                    "tool_id": tool_id,
                    "spend_today": float(spend),
                    "cost_requested": float(cost),
                    "daily_cap": float(cap)
                }
            )

    def _enforce_kpi(self, ctx: RequestContext, surface: str, action: str) -> None:
        try:
            corridors = self.kpi_service.list_corridors(ctx, surface=surface)
        except Exception as exc:
            error_response(
                code="kpi_unavailable",
                message="KPI service unavailable",
                status_code=403,
                gate="kpi",
                action_name=action,
                details={"reason": str(exc)},
            )

        if not corridors:
            if os.environ.get("GATECHAIN_ALLOW_MISSING") == "1":
                return
            error_response(
                code="kpi_threshold_missing",
                message=f"No KPI thresholds configured for {surface}",
                status_code=403,
                gate="kpi",
                action_name=action,
                details={"surface": surface},
            )

        surface_value = normalize_surface_id(surface) if surface else surface
        for corridor in corridors:
            target_surface = surface_value or surface
            if not target_surface:
                target_surface = surface or "nexus"
            measurement = self.kpi_service.latest_raw_measurement(ctx, target_surface, corridor.kpi_name)
            if measurement is None:
                continue
            if corridor.floor is not None and measurement.value < corridor.floor:
                error_response(
                    code="kpi_floor_breached",
                    message=f"KPI {corridor.kpi_name} floor breached: {measurement.value} < {corridor.floor}",
                    status_code=403,
                    gate="kpi",
                    action_name=action,
                    details={
                        "surface": target_surface,
                        "kpi_name": corridor.kpi_name,
                        "value": measurement.value,
                        "floor": corridor.floor,
                    },
                )
            if corridor.ceiling is not None and measurement.value > corridor.ceiling:
                error_response(
                    code="kpi_ceiling_breached",
                    message=f"KPI {corridor.kpi_name} ceiling breached: {measurement.value} > {corridor.ceiling}",
                    status_code=403,
                    gate="kpi",
                    action_name=action,
                    details={
                        "surface": target_surface,
                        "kpi_name": corridor.kpi_name,
                        "value": measurement.value,
                        "ceiling": corridor.ceiling,
                    },
                )

    def _enforce_temperature(self, ctx: RequestContext, surface: str, action: str) -> None:
        try:
            snapshot = self.temperature_service.compute_temperature(ctx, surface)
        except Exception as exc:
            error_response(
                code="temperature_unavailable",
                message="Temperature service unavailable",
                status_code=403,
                gate="temperature",
                action_name=action,
                details={"reason": str(exc)},
            )

        if getattr(snapshot, "floors_breached", None) or getattr(snapshot, "ceilings_breached", None):
            error_response(
                code="temperature_breach",
                message="Temperature thresholds breached",
                status_code=403,
                gate="temperature",
                action_name=action,
                details={
                    "surface": surface,
                    "floors": getattr(snapshot, "floors_breached", []),
                    "ceilings": getattr(snapshot, "ceilings_breached", []),
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
