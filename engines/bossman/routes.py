from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from engines.budget.service import get_budget_service
from engines.common.analytics import get_analytics_resolver
from engines.common.identity import RequestContext, get_request_context
from engines.firearms.models import LicenceStatus
from engines.firearms.service import DANGEROUS_ACTIONS, get_firearms_service
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.kpi.service import get_kpi_service
from engines.seo.service import get_seo_service
from engines.strategy_lock.models import StrategyStatus
from engines.strategy_lock.service import get_strategy_lock_service
from engines.temperature.service import get_temperature_service
from engines.config import runtime_config
from engines.budget.cogs import CostEstimator
from engines.kill_switch.service import get_kill_switch_service
from engines.privacy.train_prefs import get_training_pref_service
from engines.nexus.backends import get_backend

router = APIRouter(prefix="/bossman", tags=["bossman"])


@router.get("/tenant-dashboard")
def tenant_dashboard(
    surface: Optional[str] = Query(default="squared"),
    window_days: int = Query(default=7, ge=1, le=90),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    surface_name = surface or "squared"

    temp_svc = get_temperature_service()
    snapshots = temp_svc.list_snapshots(context, surface_name, limit=5)
    temperature = {
        "surface": surface_name,
        "current": snapshots[0] if snapshots else None,
        "recent": snapshots,
        "config": temp_svc.get_config_bundle(context, surface_name),
    }

    budget_svc = get_budget_service()
    budget = {
        "by_provider": budget_svc.summary(context, window_days=window_days, surface=surface_name, group_by="provider"),
        "by_model": budget_svc.summary(context, window_days=window_days, surface=surface_name, group_by="model_or_plan_id"),
        "by_tool_type": budget_svc.summary(context, window_days=window_days, surface=surface_name, group_by="tool_type"),
    }

    kpi_svc = get_kpi_service()
    kpi = {
        "definitions": kpi_svc.list_definitions(context, surface_name),
        "corridors": kpi_svc.list_corridors(context, surface_name),
    }

    lock_svc = get_strategy_lock_service()
    approved = lock_svc.list_locks(context, status=StrategyStatus.approved)
    now = datetime.now(timezone.utc)
    active_locks = [l for l in approved if (not l.valid_from or l.valid_from <= now) and (not l.valid_until or l.valid_until >= now)]
    recent_locks = sorted(lock_svc.list_locks(context), key=lambda l: l.updated_at, reverse=True)[:10]

    firearms_svc = get_firearms_service()
    firearms = {
        "active_licences": firearms_svc.list_licences(context, status=LicenceStatus.active),
        "dangerous_actions": DANGEROUS_ACTIONS,
    }

    # Event sink status
    sink_backend = (runtime_config.get_nexus_backend() or "firestore").lower()
    event_sink = {"backend": sink_backend, "last_write_at": None}
    event_sink["backend_class"] = sink_backend

    # COGS summary
    cogs = CostEstimator(budget_service=get_budget_service()).summarize(context.tenant_id, context.env)

    # Kill switch snapshot
    kill_switch = get_kill_switch_service().get(context)

    # Training/PII preferences
    prefs = get_training_pref_service().prefs_snapshot(context.tenant_id, context.env)

    analytics_resolver = get_analytics_resolver()
    analytics = {
        "effective_config": analytics_resolver.resolve(context, surface_name),
        "page_seo": get_seo_service().list(context, surface=None),
    }

    return {
        "tenant_id": context.tenant_id,
        "env": context.env,
        "surface": surface_name,
        "temperature": temperature,
        "budget": budget,
        "cogs": cogs,
        "kpi": kpi,
        "strategy_locks": {"active": active_locks, "recent": recent_locks},
        "firearms": firearms,
        "analytics": analytics,
        "event_sink": event_sink,
        "training_prefs": prefs,
        "kill_switch": kill_switch,
    }
