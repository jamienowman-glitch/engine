"""Rootsmanuva and Selecta Loop services (deterministic routing + planning stubs)."""
from __future__ import annotations

from typing import List

from engines.routing.schemas import (
    CandidateOption,
    ProposedRoutingProfileUpdate,
    RoutingContext,
    RoutingDecision,
    RoutingMetricWeight,
    RoutingProfile,
)


class RootsmanuvaService:
    def route(
        self,
        routing_profile: RoutingProfile,
        candidates: List[CandidateOption],
        context: RoutingContext,
    ) -> RoutingDecision:
        score_by_candidate = {}
        ranking = []
        flags: List[str] = []

        fallback = routing_profile.fallback
        allow_missing = fallback.allow_missing_metrics if fallback else False
        missing_penalty = fallback.missing_metric_penalty if fallback else None

        disallowed_missing_required: set[str] = set()
        for candidate in candidates:
            snap = candidate.snapshot
            metrics = snap.metrics or {}
            score = 0.0
            candidate_flags: List[str] = []

            for weight in routing_profile.metrics:
                score_delta, flag = self._score_metric(weight, metrics, allow_missing, missing_penalty)
                score += score_delta
                if flag:
                    candidate_flags.append(flag)
                    if flag.startswith("missing_required_metric") and not allow_missing and missing_penalty is None:
                        disallowed_missing_required.add(snap.candidate_id)

            if fallback:
                # Simple max cost rule if provided
                max_cost = fallback.max_cost_usd_per_day
                cost_val = metrics.get("cost.usd.per_day") or metrics.get("cost.usd.1d")
                if max_cost is not None and cost_val is not None and cost_val > max_cost:
                    candidate_flags.append("fallback_max_cost_exceeded")
                    score -= abs(cost_val - max_cost)
                # Latency cap
                max_latency = fallback.max_latency_ms_p95
                latency_val = metrics.get("latency.ms.p95")
                if max_latency is not None and latency_val is not None and latency_val > max_latency:
                    candidate_flags.append("fallback_latency_exceeded")
                    score -= abs(latency_val - max_latency)

            score_by_candidate[snap.candidate_id] = score
            flags.extend(candidate_flags)

        # Enforce hard constraints (simple disallow list)
        def _is_allowed(opt: CandidateOption) -> bool:
            constraints = opt.hard_constraints or {}
            disallow_vendor = constraints.get("disallow_vendor", [])
            if opt.snapshot.vendor in disallow_vendor:
                return False
            min_eval = constraints.get("min_eval_quality")
            if min_eval is not None:
                if opt.snapshot.metrics.get("eval.quality.avg", 0.0) < min_eval:
                    return False
            return True

        allowed = [
            c
            for c in candidates
            if _is_allowed(c) and c.snapshot.candidate_id not in disallowed_missing_required
        ]
        ranking = sorted(
            [c.snapshot.candidate_id for c in allowed],
            key=lambda cid: score_by_candidate.get(cid, float("-inf")),
            reverse=True,
        )
        selected = ranking[0] if ranking else None

        return RoutingDecision(
            routing_profile_id=routing_profile.id,
            requested_at=context.timestamp,
            tenant_id=context.tenant_id,
            surface_id=context.surface_id,
            app_id=context.app_id,
            candidates=candidates,
            selected_candidate_id=selected,
            ranking=ranking,
            score_by_candidate=score_by_candidate,
            flags=flags if flags else None,
        )

    def _score_metric(
        self,
        weight: RoutingMetricWeight,
        metrics: dict,
        allow_missing: bool,
        missing_penalty: float | None,
    ) -> tuple[float, str | None]:
        value = metrics.get(weight.key)
        direction = weight.direction
        if direction is None:
            direction = "higher_is_better" if weight.weight >= 0 else "lower_is_better"
        if value is None:
            if weight.required and not allow_missing:
                if missing_penalty is not None:
                    return -abs(missing_penalty), f"missing_required_metric:{weight.key}"
                return float("-inf"), f"missing_required_metric:{weight.key}"
            return 0.0, f"missing_metric:{weight.key}"
        if direction == "lower_is_better":
            return weight.weight * (-value), None
        return weight.weight * value, None


class SelectaLoopService:
    def propose_profile_update(
        self,
        profile: RoutingProfile,
        decision_history: List[RoutingDecision],
        metric_trends: List[dict],
        context: RoutingContext,
    ) -> ProposedRoutingProfileUpdate:
        # Planning stub: return the same profile with a summary placeholder.
        return ProposedRoutingProfileUpdate(
            profile_id=profile.id,
            current_profile=profile,
            suggested_profile=profile,
            summary="No-op suggestion (placeholder until selector agent is wired).",
            source=None,
            confidence=None,
        )
