"""Budget ingestion and enforcement services."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.budget.schemas import CostRecord, UsageMetric


class BudgetIngestor:
    """Normalize cloud billing/usage into UsageMetric/CostRecord."""

    def __init__(self, vertex_client=None, bedrock_client=None):
        self._vertex_client = vertex_client
        self._bedrock_client = bedrock_client

    def ingest_vertex_usage(self, tenant_id: str, timeframe: str) -> List[UsageMetric]:
        if not self._vertex_client:
            return []
        raw = self._vertex_client.list_usage(timeframe=timeframe)
        return [
            UsageMetric(
                tenant_id=tenant_id,
                vendor="vertex",
                model=item.get("model", ""),
                tokens=item.get("tokens"),
                calls=item.get("calls"),
                cost_estimate=item.get("cost"),
                timeframe=timeframe,
                metadata={"project": item.get("project", "")},
            )
            for item in raw
        ]

    def ingest_bedrock_usage(self, tenant_id: str, timeframe: str) -> List[UsageMetric]:
        if not self._bedrock_client:
            return []
        raw = self._bedrock_client.list_usage(timeframe=timeframe)
        return [
            UsageMetric(
                tenant_id=tenant_id,
                vendor="bedrock",
                model=item.get("model", ""),
                tokens=item.get("tokens"),
                calls=item.get("calls"),
                cost_estimate=item.get("cost"),
                timeframe=timeframe,
                metadata={"region": item.get("region", "")},
            )
            for item in raw
        ]

    def ingest_cost_records(self, tenant_id: str, vendor: str, data: List[Dict[str, Any]], period: str) -> List[CostRecord]:
        records = []
        for item in data:
            records.append(
                CostRecord(
                    tenant_id=tenant_id,
                    vendor=vendor,
                    service=item.get("service", vendor),
                    cost=item.get("cost", 0.0),
                    period=period,
                    source_ref=item.get("source_ref"),
                )
            )
        return records


class BudgetService:
    """Budget enforcement decisions."""

    def __init__(self, corridors: Optional[Dict[str, Dict[str, float]]] = None):
        self._corridors = corridors or {}

    def evaluate_call(self, request_context: Dict[str, Any], usage_hint: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = request_context.get("tenant_id")
        vendor = usage_hint.get("vendor")
        model = usage_hint.get("model")
        estimated_cost = usage_hint.get("cost_estimate", 0.0)
        corridor = self._corridors.get(tenant_id, {}).get(model or vendor, {})
        cap = corridor.get("cap")
        if cap is not None and estimated_cost and estimated_cost > cap:
            return {"decision": "deny", "reason": "budget_cap_exceeded"}
        if cap is not None and estimated_cost and estimated_cost > 0.8 * cap:
            return {"decision": "needs_HITL", "reason": "near_budget_cap"}
        return {"decision": "allow"}
