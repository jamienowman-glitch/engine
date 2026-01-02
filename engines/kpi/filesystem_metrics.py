"""Filesystem-backed metrics store adapter for raw KPI ingestion (Lane 2 adapter).

Stores raw metric data points (JSONL) with query-by-scope interface.
Location: var/metrics_store/{tenant_id}/{env}/{surface_id or "_"}/raw.jsonl
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id

logger = logging.getLogger(__name__)


class FileSystemMetricsStore:
    """Filesystem-backed metrics store using JSONL append-log.
    
    Path structure:
      var/metrics_store/{tenant_id}/{env}/{surface_id or "_"}/raw.jsonl
    
    Each line is: {
      "metric_name": str,
      "value": float | int,
      "timestamp": ISO-8601,
      "tags": {optional dict for filtering},
      "source": str  (e.g. "system", "agent", "user")
    }
    """
    
    def __init__(self, base_dir: Optional[str | Path] = None) -> None:
        self._base_dir = Path(base_dir or Path.cwd() / "var" / "metrics_store")
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _metrics_dir(self, context: RequestContext) -> Path:
        """Deterministic directory path for metrics."""
        surface = normalize_surface_id(context.surface_id) if context.surface_id else "_"
        env = (context.env or "dev").lower()
        tenant = context.tenant_id
        
        return self._base_dir / tenant / env / surface
    
    def _raw_file(self, context: RequestContext) -> Path:
        """Full path to the raw metrics JSONL file."""
        return self._metrics_dir(context) / "raw.jsonl"
    
    def ingest(
        self, 
        metric_name: str, 
        value: float | int,
        context: RequestContext,
        tags: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> None:
        """Append a raw metric data point."""
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=metrics_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        metrics_dir = self._metrics_dir(context)
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        raw_file = self._raw_file(context)
        
        record = {
            "metric_name": metric_name,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tags": tags or {},
            "source": source or "system",
        }
        
        try:
            with open(raw_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as exc:
            logger.error(f"Failed to ingest metric to {raw_file}: {exc}")
            raise RuntimeError(f"Metrics ingest failed: {exc}") from exc
    
    def query(
        self, 
        metric_name: Optional[str] = None,
        context: Optional[RequestContext] = None,
    ) -> List[Dict[str, Any]]:
        """Query raw metrics, optionally filtered by metric_name.
        
        Returns all records (or filtered by metric_name) in append order.
        """
        if context is None:
            logger.warning(
                "query called without RequestContext; assuming default env=dev, surface=_"
            )
            from engines.common.identity import RequestContext as RC
            context = RC(tenant_id="t_system", env="dev")
        
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=metrics_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        raw_file = self._raw_file(context)
        
        if not raw_file.exists():
            return []
        
        results = []
        try:
            with open(raw_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if metric_name is None or record.get("metric_name") == metric_name:
                            results.append(record)
                    except Exception as exc:
                        logger.warning(f"Skipping malformed metrics line in {raw_file}: {exc}")
        except Exception as exc:
            logger.error(f"Failed to query metrics from {raw_file}: {exc}")
        
        return results
    
    def get_latest(
        self, 
        metric_name: str,
        context: RequestContext,
    ) -> Optional[Dict[str, Any]]:
        """Get the latest value for a metric."""
        # Enforce backend-class guard: filesystem forbidden in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=metrics_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        records = self.query(metric_name, context)
        return records[-1] if records else None
