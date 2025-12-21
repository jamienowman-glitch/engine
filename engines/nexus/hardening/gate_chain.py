from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from fastapi import HTTPException

from engines.budget.service import BudgetService, get_budget_service
from engines.common.identity import RequestContext
from engines.firearms.service import DANGEROUS_ACTIONS, FirearmsService, get_firearms_service
from engines.kill_switch.service import KillSwitchService, get_kill_switch_service
from engines.kpi.service import KpiService, get_kpi_service
from engines.logging.audit import emit_audit_event
from engines.strategy_lock.service import StrategyLockService, get_strategy_lock_service
from engines.temperature.service import TemperatureService, get_temperature_service


BudgetThresholdResolver = Callable[[Optional[str]], Optional[Decimal]]


def _normalize_surface(surface: Optional[str]) -> str:
    if not surface:
        return "DEFAULT"
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in surface.strip().upper())
    return cleaned or "DEFAULT"


def _build_budget_env(surface: Optional[str]) -> str:
    normalized = _normalize_surface(surface)
    return f"BUDGET_MAX_COST_{normalized}"


def _default_budget_threshold(surface: Optional[str]) -> Optional[Decimal]:
    candidates = [_build_budget_env(surface), "BUDGET_MAX_COST"]
    for key in candidates:
        value = os.getenv(key)
        if value:
            try:
                return Decimal(value)
            except InvalidOperation:
                continue
    return None


class GateChain:
    def __init__(
        self,
        kill_switch_service: Optional[KillSwitchService] = None,
        firearms_service: Optional[FirearmsService] = None,
        strategy_lock_service: Optional[StrategyLockService] = None,
        budget_service: Optional[BudgetService] = None,
        kpi_service: Optional[KpiService] = None,
        temperature_service: Optional[TemperatureService] = None,
        budget_threshold_resolver: BudgetThresholdResolver = _default_budget_threshold,
        audit_logger: Callable = emit_audit_event,
    ):
        self.kill_switch = kill_switch_service or get_kill_switch_service()
        self.firearms = firearms_service or get_firearms_service()
        self.strategy_lock = strategy_lock_service or get_strategy_lock_service()
        self.budget_service = budget_service or get_budget_service()
        self.kpi_service = kpi_service or get_kpi_service()
        self.temperature_service = temperature_service or get_temperature_service()
        self._budget_threshold_resolver = budget_threshold_resolver
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
        self.kill_switch.ensure_action_allowed(ctx, action)

        if action in DANGEROUS_ACTIONS:
            self.firearms.require_licence_or_raise(ctx, subject_type or "unknown", subject_id or action, action)

        self.strategy_lock.require_strategy_lock_or_raise(ctx, surface_key, action)

        if not skip_metrics:
            self._enforce_budget(ctx, surface_key, action)
            self._enforce_kpi(ctx, surface_key, action)
            self._enforce_temperature(ctx, surface_key, action)

        self._emit_audit(ctx, action, surface_key, subject_type, subject_id, skip_metrics)

    def _enforce_budget(self, ctx: RequestContext, surface: str, action: str) -> None:
        threshold = self._budget_threshold_resolver(surface)
        if threshold is None:
            if os.environ.get("GATECHAIN_ALLOW_MISSING") == "1":
                return
            raise HTTPException(
                status_code=403,
                detail={"error": "budget_threshold_missing", "surface": surface},
            )

        try:
            summary = self.budget_service.summary(ctx, surface=surface)
        except Exception as exc:
            raise HTTPException(status_code=403, detail={"error": "budget_unavailable", "reason": str(exc)})

        total_cost = summary.get("total_cost")
        try:
            total = Decimal(str(total_cost))
        except (InvalidOperation, TypeError):
            total = Decimal("0")

        if total > threshold:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "budget_threshold_exceeded",
                    "surface": surface,
                    "total_cost": float(total),
                    "threshold": float(threshold),
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
