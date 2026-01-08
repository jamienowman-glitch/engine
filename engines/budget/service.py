"""Budget usage service with cost/summary helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from engines.budget.models import UsageEvent
from engines.budget.repository import BudgetUsageRepository, budget_repo_from_env
from engines.common.identity import RequestContext
from engines.common.aws_runtime import aws_identity
from engines.kill_switch.service import get_kill_switch_service
from engines.logging.events.contract import StorageClass


class BudgetService:
    def __init__(self, repo: Optional[BudgetUsageRepository] = None) -> None:
        self.repo = repo or budget_repo_from_env()

    def record_usage(self, ctx: RequestContext, events: List[UsageEvent]) -> List[UsageEvent]:
        saved: List[UsageEvent] = []
        for ev in events:
            ev.tenant_id = ctx.tenant_id
            ev.env = ctx.env
            get_kill_switch_service().ensure_provider_allowed(ctx, ev.provider)
            if (ev.provider or "").lower() == "aws":
                self._attach_aws_metadata(ev)
            ev.mode = ev.mode or ctx.mode
            ev.project_id = ev.project_id or ctx.project_id
            ev.request_id = ev.request_id or ctx.request_id
            ev.trace_id = ev.trace_id or ctx.request_id
            ev.run_id = ev.run_id or ctx.request_id
            ev.step_id = ev.step_id or f"usage.{ev.tool_type or ev.tool_id or 'event'}"
            ev.storage_class = StorageClass.COST
            saved.append(self.repo.record_usage(ev))
        return saved

    def query_usage(
        self,
        ctx: RequestContext,
        surface: Optional[str] = None,
        provider: Optional[str] = None,
        model_or_plan_id: Optional[str] = None,
        tool_type: Optional[str] = None,
        window_days: int = 7,
        limit: int = 200,
        offset: int = 0,
    ) -> List[UsageEvent]:
        until = datetime.now(timezone.utc)
        since = until - timedelta(days=window_days)
        return self.repo.list_usage(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface=surface,
            provider=provider,
            model_or_plan_id=model_or_plan_id,
            tool_type=tool_type,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    def get_tool_spend(
        self,
        ctx: RequestContext,
        tool_id: str,
        window_days: int = 1
    ) -> Decimal:
        """Calculate total spend for a tool over the last N days."""
        until = datetime.now(timezone.utc)
        since = until - timedelta(days=window_days)
        events = self.repo.list_usage(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            tool_id=tool_id,
            since=since,
            until=until,
            limit=10_000 # Assume reasonable limit for aggregation
        )
        total = sum((ev.cost for ev in events), Decimal("0"))
        return total

    def summary(
        self,
        ctx: RequestContext,
        window_days: int = 7,
        surface: Optional[str] = None,
        group_by: Optional[str] = "provider",
    ) -> Dict[str, object]:
        until = datetime.now(timezone.utc)
        since = until - timedelta(days=window_days)
        totals = self.repo.get_totals(
            tenant_id=ctx.tenant_id, env=ctx.env, since=since, until=until, surface=surface, group_by=group_by
        )
        grouped = {k: {"cost": float(v["cost"]), "count": v["count"]} for k, v in totals["grouped"].items()}
        return {
            "window_days": window_days,
            "total_cost": float(totals["total_cost"]),
            "total_events": totals["total_events"],
            "grouped": grouped,
        }

    @staticmethod
    def _attach_aws_metadata(event: UsageEvent) -> None:
        meta = event.metadata or {}
        if "aws_account_id" in meta and "aws_principal_arn" in meta:
            event.metadata = meta
            return
        try:
            ident = aws_identity()
            meta.setdefault("aws_account_id", ident.get("account_id"))
            meta.setdefault("aws_principal_arn", ident.get("arn"))
            meta.setdefault("aws_region", ident.get("region"))
        except Exception as exc:
            meta.setdefault("aws_identity_error", str(exc))
        event.metadata = meta


_default_service: Optional[BudgetService] = None


def get_budget_service() -> BudgetService:
    global _default_service
    if _default_service is None:
        _default_service = BudgetService()
    return _default_service


def set_budget_service(service: BudgetService) -> None:
    global _default_service
    _default_service = service
