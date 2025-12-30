from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from engines.budget.models import UsageEvent
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.service import BudgetService, set_budget_service
from engines.chat.service.server import create_app
from engines.common.analytics import AnalyticsResolver, set_analytics_resolver
from engines.common.identity import RequestContext
from engines.firearms.models import FirearmsLicence, LicenceLevel
from engines.firearms.repository import InMemoryFirearmsRepository
from engines.firearms.service import FirearmsService, set_firearms_service
from engines.identity.analytics_service import AnalyticsConfigService, set_analytics_service
from engines.identity.jwt_service import default_jwt_service
from engines.identity.models import Tenant, TenantAnalyticsConfig, TenantMembership, User
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.kpi.models import KpiCorridor, KpiDefinition
from engines.kpi.repository import InMemoryKpiRepository
from engines.kpi.service import KpiService, set_kpi_service
from engines.seo.models import PageSeoConfig
from engines.seo.repository import InMemorySeoRepository
from engines.seo.service import SeoService, set_seo_service
from engines.strategy_lock.models import StrategyLock, StrategyStatus
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.temperature.models import CeilingConfig, FloorConfig, TemperatureSnapshot, TemperatureWeights
from engines.temperature.repository import InMemoryTemperatureRepository
from engines.temperature.service import TemperatureService, set_temperature_service
from engines.privacy.train_prefs import TrainingPreferenceService, set_training_pref_service
from engines.kill_switch.service import set_kill_switch_service, KillSwitchService


def _setup_identity() -> tuple[RequestContext, dict, InMemoryIdentityRepository]:
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    user = repo.create_user(User(email="bossman@example.com", password_hash="pw"))
    tenant = repo.create_tenant(Tenant(id="t_demo", name="Demo"))
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    token = default_jwt_service().issue_token(
        {"sub": user.id, "email": user.email, "tenant_ids": [tenant.id], "default_tenant_id": tenant.id, "role_map": {tenant.id: "owner"}}
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
    }
    ctx = RequestContext(tenant_id=tenant.id, mode="saas", project_id="p_demo", user_id=user.id)
    return ctx, headers, repo


def test_bossman_dashboard_returns_scoped_state():
    ctx, headers, identity_repo = _setup_identity()
    # Shared repos/services
    usage_repo = InMemoryBudgetUsageRepository()

    temp_repo = InMemoryTemperatureRepository()
    temp_service = TemperatureService(repo=temp_repo, usage_repo=usage_repo)
    set_temperature_service(temp_service)

    kpi_repo = InMemoryKpiRepository()
    kpi_service = KpiService(repo=kpi_repo)
    set_kpi_service(kpi_service)

    seo_repo = InMemorySeoRepository()
    seo_service = SeoService(repo=seo_repo)
    set_seo_service(seo_service)

    sl_repo = InMemoryStrategyLockRepository()
    sl_service = StrategyLockService(repo=sl_repo)
    set_strategy_lock_service(sl_service)

    firearms_repo = InMemoryFirearmsRepository()
    firearms_service = FirearmsService(repo=firearms_repo)
    set_firearms_service(firearms_service)

    analytics_service = AnalyticsConfigService(repo=identity_repo)
    set_analytics_service(analytics_service)
    set_analytics_resolver(AnalyticsResolver(service=analytics_service))
    set_training_pref_service(TrainingPreferenceService())
    set_kill_switch_service(KillSwitchService())

    # Seed temperature configs + snapshot
    temp_service.upsert_floor(ctx, FloorConfig(tenant_id=ctx.tenant_id, env=ctx.env, surface="squared", performance_floors={"weekly_leads": 5}))
    temp_service.upsert_ceiling(ctx, CeilingConfig(tenant_id=ctx.tenant_id, env=ctx.env, surface="squared", ceilings={"complaint_rate": 0.2}))
    temp_service.upsert_weights(ctx, TemperatureWeights(tenant_id=ctx.tenant_id, env=ctx.env, surface="squared", weights={"weekly_leads": 1.0}))
    now = datetime.now(timezone.utc)
    temp_repo.save_snapshot(
        TemperatureSnapshot(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="squared",
            value=0.5,
            window_start=now - timedelta(days=7),
            window_end=now,
            floors_breached=[],
            ceilings_breached=[],
            raw_metrics={"weekly_leads": 10},
            source="test",
            usage_window_days=7,
            kpi_corridors_used=[],
        )
    )

    # Seed budget usage
    budget_service = BudgetService(repo=usage_repo)
    set_budget_service(budget_service)
    budget_service.record_usage(
        ctx,
        [
            UsageEvent(
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                surface="squared",
                provider="openai",
                model_or_plan_id="gpt-4o",
                tool_type="chat",
                cost=0.25,
            ),
            UsageEvent(
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                surface="squared",
                provider="vertex",
                model_or_plan_id="gemini",
                tool_type="embedding",
                cost=0.1,
            ),
        ],
    )

    # Seed KPI, strategy lock, firearms, SEO, analytics
    kpi_service.create_definition(ctx, KpiDefinition(tenant_id=ctx.tenant_id, env=ctx.env, surface="squared", name="weekly_leads"))
    kpi_service.upsert_corridor(
        ctx, KpiCorridor(tenant_id=ctx.tenant_id, env=ctx.env, surface="squared", kpi_name="weekly_leads", floor=5, ceiling=20)
    )

    lock = StrategyLock(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        surface="squared",
        scope="campaign",
        title="Freeze",
        allowed_actions=["*"],
        created_by_user_id=ctx.user_id or "u1",
        status=StrategyStatus.approved,
    )
    sl_repo.create(lock)

    firearms_service.issue_licence(
        ctx,
        FirearmsLicence(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            subject_type="agent",
            subject_id="agent-1",
            level=LicenceLevel.medium,
        ),
    )

    seo_service.upsert(
        ctx,
        PageSeoConfig(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="squared",
            page_type="home",
            title="Home",
            description="Welcome",
        ),
    )
    analytics_service.upsert_config(
        TenantAnalyticsConfig(tenant_id=ctx.tenant_id, env=ctx.env, surface="squared", ga4_measurement_id="G-TEST")
    )

    client = TestClient(create_app())
    resp = client.get("/bossman/tenant-dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == ctx.tenant_id
    assert body["env"] == ctx.env
    assert body["temperature"]["current"] is not None
    assert body["budget"]["by_provider"]["total_events"] == 2
    assert body["kpi"]["definitions"]
    assert body["strategy_locks"]["active"]
    assert body["firearms"]["active_licences"]
    assert body["analytics"]["page_seo"]
    assert "event_sink" in body
    assert "cogs" in body
    assert "kill_switch" in body
    assert "training_prefs" in body
