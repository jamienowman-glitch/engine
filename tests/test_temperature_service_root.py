from __future__ import annotations

from datetime import datetime, timedelta

from engines.common.identity import RequestContext
from engines.temperature.models import CeilingConfig, FloorConfig, TemperatureWeights
from engines.temperature.service import TemperatureService
from engines.temperature.repository import InMemoryTemperatureRepository


def test_compute_temperature_with_breaches_and_weights():
    repo = InMemoryTemperatureRepository()
    svc = TemperatureService(repo=repo)
    ctx = RequestContext(request_id="r1", tenant_id="t_demo", env="dev")
    svc.upsert_floor(
        ctx,
        FloorConfig(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="squared",
            performance_floors={"weekly_leads": 50},
            cadence_floors={"email_campaigns_per_week": 3},
        ),
    )
    svc.upsert_ceiling(
        ctx,
        CeilingConfig(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="squared",
            ceilings={"complaint_rate": 0.05},
        ),
    )
    svc.upsert_weights(
        ctx,
        TemperatureWeights(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface="squared",
            weights={"weekly_leads": 1.0, "email_campaigns_per_week": 0.5},
            source="tenant_override",
        ),
    )

    metrics = {
        "weekly_leads": 40,  # below floor
        "email_campaigns_per_week": 4,  # above cadence floor
        "complaint_rate": 0.1,  # above ceiling
    }
    snap = svc.compute_temperature(ctx, "squared", window_days=7, metrics=metrics)
    assert "weekly_leads" in snap.floors_breached
    assert "email_campaigns_per_week" not in snap.floors_breached
    assert "complaint_rate" in snap.ceilings_breached
    assert snap.value != 0
    assert snap.raw_metrics["weekly_leads"] == 40


def test_history_listing_order():
    repo = InMemoryTemperatureRepository()
    svc = TemperatureService(repo=repo)
    ctx = RequestContext(request_id="r1", tenant_id="t_demo", env="dev")
    now = datetime.utcnow()
    metrics = {"m": 1}
    svc.compute_temperature(ctx, "squared", metrics=metrics)
    # add older
    svc.compute_temperature(ctx, "squared", metrics=metrics)
    snaps = repo.list_snapshots("t_demo", "dev", "squared", limit=2, offset=0)
    assert len(snaps) == 2
    assert snaps[0].created_at >= snaps[1].created_at

