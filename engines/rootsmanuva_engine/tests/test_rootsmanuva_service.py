from __future__ import annotations

from datetime import datetime, timezone

from engines.rootsmanuva_engine.service import RootsmanuvaService
from engines.routing.schemas import (
    CandidateOption,
    ModelMetricsSnapshot,
    RoutingContext,
    RoutingMetricWeight,
    RoutingProfile,
)


def _context():
    return RoutingContext(
        tenant_id="t_demo",
        surface_id="surface1",
        app_id="app1",
        episode_id=None,
        request_kind="llm.text",
        timestamp=datetime.now(timezone.utc),
    )


def test_selects_highest_score():
    profile = RoutingProfile(
        id="prof1",
        label="test",
        metrics=[RoutingMetricWeight(key="eval.quality.avg", weight=1.0)],
    )
    c1 = CandidateOption(
        snapshot=ModelMetricsSnapshot(
            candidate_id="c1",
            vendor="gcp",
            model_id="g1",
            tenant_id="t_demo",
            metrics={"eval.quality.avg": 0.8},
        )
    )
    c2 = CandidateOption(
        snapshot=ModelMetricsSnapshot(
            candidate_id="c2",
            vendor="aws",
            model_id="a1",
            tenant_id="t_demo",
            metrics={"eval.quality.avg": 0.9},
        )
    )
    svc = RootsmanuvaService()
    decision = svc.route(profile, [c1, c2], _context())
    assert decision.selected_candidate_id == "c2"
    assert decision.ranking[0] == "c2"


def test_missing_required_metric_drops_candidate():
    profile = RoutingProfile(
        id="prof1",
        label="test",
        metrics=[RoutingMetricWeight(key="eval.quality.avg", weight=1.0, required=True)],
        fallback=None,
    )
    c1 = CandidateOption(
        snapshot=ModelMetricsSnapshot(
            candidate_id="c1",
            vendor="gcp",
            model_id="g1",
            tenant_id="t_demo",
            metrics={},
        )
    )
    c2 = CandidateOption(
        snapshot=ModelMetricsSnapshot(
            candidate_id="c2",
            vendor="aws",
            model_id="a1",
            tenant_id="t_demo",
            metrics={"eval.quality.avg": 0.5},
        )
    )
    svc = RootsmanuvaService()
    decision = svc.route(profile, [c1, c2], _context())
    assert decision.selected_candidate_id == "c2"
    assert decision.ranking == ["c2"]


def test_hard_constraints_block_vendor():
    profile = RoutingProfile(
        id="prof1",
        label="test",
        metrics=[RoutingMetricWeight(key="eval.quality.avg", weight=1.0)],
    )
    c1 = CandidateOption(
        snapshot=ModelMetricsSnapshot(
            candidate_id="c1",
            vendor="aws",
            model_id="a1",
            tenant_id="t_demo",
            metrics={"eval.quality.avg": 1.0},
        ),
        hard_constraints={"disallow_vendor": ["aws"]},
    )
    c2 = CandidateOption(
        snapshot=ModelMetricsSnapshot(
            candidate_id="c2",
            vendor="gcp",
            model_id="g1",
            tenant_id="t_demo",
            metrics={"eval.quality.avg": 0.7},
        )
    )
    svc = RootsmanuvaService()
    decision = svc.route(profile, [c1, c2], _context())
    assert decision.selected_candidate_id == "c2"
    assert "c2" in decision.ranking
