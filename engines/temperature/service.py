"""Temperature service: manage floors/ceilings/weights and compute snapshots."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id
from engines.budget.repository import InMemoryBudgetUsageRepository, BudgetUsageRepository
from engines.kpi.service import get_kpi_service
from engines.temperature.models import (
    CeilingConfig,
    FloorConfig,
    TemperatureSnapshot,
    TemperatureWeights,
)
from engines.temperature.repository import FileTemperatureRepository, InMemoryTemperatureRepository, TemperatureRepository


def _resolve_surface(surface: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    candidate = surface or fallback
    return normalize_surface_id(candidate)


class TemperatureMetricsAdapter:
    """Adapter interface for sourcing metrics (usage/logs/budget)."""

    source_id = "unknown"

    def fetch_metrics(
        self, ctx: RequestContext, surface: str, window_start: datetime, window_end: datetime, metric_keys: Optional[list[str]] = None
    ) -> Dict[str, float]:
        raise NotImplementedError


class InMemoryMetricsAdapter(TemperatureMetricsAdapter):
    source_id = "in_memory"

    def __init__(self, usage_repo: UsageRepository) -> None:
        self.usage_repo = usage_repo

    def fetch_metrics(
        self, ctx: RequestContext, surface: str, window_start: datetime, window_end: datetime, metric_keys: Optional[list[str]] = None
    ) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        records = self.usage_repo.list_usage(ctx.tenant_id, ctx.env, surface=surface, since=window_start, until=window_end, limit=5000)
        for rec in records:
            if metric_keys and rec.metadata:
                for key in metric_keys:
                    if key in rec.metadata:
                        metrics[key] = metrics.get(key, 0.0) + float(rec.metadata.get(key, 0))
        return metrics


class ExternalMetricsAdapter(TemperatureMetricsAdapter):
    """Placeholder for future external metrics (e.g., BigQuery/Grafana/budget service)."""

    source_id = "external_stub"

    def fetch_metrics(
        self, ctx: RequestContext, surface: str, window_start: datetime, window_end: datetime, metric_keys: Optional[list[str]] = None
    ) -> Dict[str, float]:
        # TODO: implement real external lookup using metrics_primary slot via SELECTA
        return {}


class TemperatureService:
    def __init__(
        self,
        repo: Optional[TemperatureRepository] = None,
        usage_repo: Optional[BudgetUsageRepository] = None,
        metrics_adapter: Optional[TemperatureMetricsAdapter] = None,
    ) -> None:
        self.repo = repo or FileTemperatureRepository()
        self.usage_repo = usage_repo or InMemoryBudgetUsageRepository()
        self.metrics_adapter = metrics_adapter or InMemoryMetricsAdapter(self.usage_repo)

    # Config management
    def upsert_floor(self, ctx: RequestContext, cfg: FloorConfig) -> FloorConfig:
        resolved_surface = _resolve_surface(cfg.surface, ctx.surface_id)
        if not resolved_surface:
            raise ValueError("surface is required")
        cfg.surface = resolved_surface
        cfg.tenant_id = ctx.tenant_id
        cfg.env = ctx.env
        return self.repo.upsert_floor(cfg)

    def upsert_ceiling(self, ctx: RequestContext, cfg: CeilingConfig) -> CeilingConfig:
        resolved_surface = _resolve_surface(cfg.surface, ctx.surface_id)
        if not resolved_surface:
            raise ValueError("surface is required")
        cfg.surface = resolved_surface
        cfg.tenant_id = ctx.tenant_id
        cfg.env = ctx.env
        return self.repo.upsert_ceiling(cfg)

    def upsert_weights(self, ctx: RequestContext, cfg: TemperatureWeights) -> TemperatureWeights:
        resolved_surface = _resolve_surface(cfg.surface, ctx.surface_id)
        if not resolved_surface:
            raise ValueError("surface is required")
        cfg.surface = resolved_surface
        cfg.tenant_id = ctx.tenant_id
        cfg.env = ctx.env
        return self.repo.upsert_weights(cfg)

    def get_config_bundle(self, ctx: RequestContext, surface: str) -> Dict[str, object]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        if not surface_value:
            raise ValueError("surface is required")
        return {
            "floors": self.repo.get_floor(ctx.tenant_id, ctx.env, surface_value),
            "ceilings": self.repo.get_ceiling(ctx.tenant_id, ctx.env, surface_value),
            "weights": self.repo.get_weights(ctx.tenant_id, ctx.env, surface_value),
        }

    def list_snapshots(self, ctx: RequestContext, surface: str, limit: int = 20, offset: int = 0) -> List[TemperatureSnapshot]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        if not surface_value:
            raise ValueError("surface is required")
        return self.repo.list_snapshots(ctx.tenant_id, ctx.env, surface_value, limit=limit, offset=offset)

    # Temperature computation
    def compute_temperature(
        self,
        ctx: RequestContext,
        surface: str,
        window_days: int = 7,
        metrics: Optional[Dict[str, float]] = None,
    ) -> TemperatureSnapshot:
        """Compute deterministic temperature from floors/ceilings/weights."""
        surface_value = _resolve_surface(surface, ctx.surface_id)
        if not surface_value:
            raise ValueError("surface is required")
        floor_cfg = self.repo.get_floor(ctx.tenant_id, ctx.env, surface_value)
        ceiling_cfg = self.repo.get_ceiling(ctx.tenant_id, ctx.env, surface_value)
        weights_cfg = self.repo.get_weights(ctx.tenant_id, ctx.env, surface_value) or TemperatureWeights(
            tenant_id=ctx.tenant_id, env=ctx.env, surface=surface_value, weights={}
        )

        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=window_days)

        metric_keys = list(weights_cfg.weights.keys())
        if floor_cfg:
            metric_keys.extend(list(floor_cfg.performance_floors.keys()))
            metric_keys.extend(list(floor_cfg.cadence_floors.keys()))
        if ceiling_cfg:
            metric_keys.extend(list(ceiling_cfg.ceilings.keys()))
        raw_metrics = metrics or self._fetch_metrics(ctx, surface_value, window_start, window_end, metric_keys=metric_keys)
        floors_breached = self._breaches(raw_metrics, floor_cfg.performance_floors if floor_cfg else {})
        cadence_breaches = self._breaches(raw_metrics, floor_cfg.cadence_floors if floor_cfg else {})
        ceilings_breached = self._ceilings(raw_metrics, ceiling_cfg.ceilings if ceiling_cfg else {})

        score = self._aggregate(raw_metrics, weights_cfg.weights)
        corridor_names = self._corridor_names(ctx, surface_value)
        snapshot = TemperatureSnapshot(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            surface=surface_value,
            value=score,
            window_start=window_start,
            window_end=window_end,
            floors_breached=floors_breached + cadence_breaches,
            ceilings_breached=ceilings_breached,
            raw_metrics=raw_metrics,
            source=getattr(self.metrics_adapter, "source_id", "in_memory"),
            usage_window_days=window_days,
            kpi_corridors_used=corridor_names,
        )
        return self.repo.save_snapshot(snapshot)

    def propose_weight_updates(
        self,
        ctx: RequestContext,
        surface: str,
        history: List[TemperatureSnapshot],
    ) -> TemperatureWeights:
        """Placeholder: to be implemented by LLM tuning job."""
        raise NotImplementedError("LLM tuning not implemented; this is a contract placeholder.")

    # --- Helpers ---
    def _fetch_metrics(
        self, ctx: RequestContext, surface: str, window_start: datetime, window_end: datetime, metric_keys: Optional[list[str]] = None
    ) -> Dict[str, float]:
        """Aggregate metrics via adapter."""
        return self.metrics_adapter.fetch_metrics(ctx, surface, window_start, window_end, metric_keys=metric_keys)

    @staticmethod
    def _breaches(actuals: Dict[str, float], mins: Dict[str, float]) -> List[str]:
        return [k for k, v in mins.items() if actuals.get(k, 0) < v]

    @staticmethod
    def _ceilings(actuals: Dict[str, float], maxes: Dict[str, float]) -> List[str]:
        return [k for k, v in maxes.items() if actuals.get(k, 0) > v]

    @staticmethod
    def _aggregate(actuals: Dict[str, float], weights: Dict[str, float]) -> float:
        if not weights:
            return 0.0
        total_weight = sum(abs(w) for w in weights.values()) or 1.0
        score = 0.0
        for key, weight in weights.items():
            score += actuals.get(key, 0.0) * weight
        return score / total_weight

    @staticmethod
    def _corridor_names(ctx: RequestContext, surface: str) -> List[str]:
        try:
            svc = get_kpi_service()
            corridors = svc.list_corridors(ctx, surface=surface)
            return [c.kpi_name for c in corridors]
        except Exception:
            return []


_default_service: Optional[TemperatureService] = None


def get_temperature_service() -> TemperatureService:
    global _default_service
    if _default_service is None:
        _default_service = TemperatureService()
    return _default_service


def set_temperature_service(svc: TemperatureService) -> None:
    global _default_service
    _default_service = svc
