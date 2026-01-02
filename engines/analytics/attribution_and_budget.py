"""Builder B: Attribution Contracts and Budget/Usage tracking.

Both use tabular_store under the hood (configured via routing).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.storage.routing_service import TabularStoreService

logger = logging.getLogger(__name__)


class AttributionContract:
    """Attribution contract: platform + utm template + allowed fields + version."""
    
    def __init__(
        self,
        platform: str,
        utm_template: Dict[str, str],
        allowed_fields: List[str],
        version: int = 1,
    ) -> None:
        self.platform = platform
        self.utm_template = utm_template  # e.g., {"source": "google", "medium": "cpc"}
        self.allowed_fields = allowed_fields  # e.g., ["campaign", "content", "term"]
        self.version = version
        self.created_at = datetime.now(timezone.utc).isoformat()
    
    def dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "utm_template": self.utm_template,
            "allowed_fields": self.allowed_fields,
            "version": self.version,
            "created_at": self.created_at,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> AttributionContract:
        return AttributionContract(
            platform=data["platform"],
            utm_template=data.get("utm_template", {}),
            allowed_fields=data.get("allowed_fields", []),
            version=data.get("version", 1),
        )


class AttributionService:
    """Manage attribution contracts via tabular store."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._tabular_service = TabularStoreService(context)
    
    def save_contract(self, contract: AttributionContract) -> None:
        """Save attribution contract."""
        try:
            self._tabular_service.upsert(
                "attribution_contracts",
                f"contract#{contract.platform}",
                contract.dict(),
            )
        except Exception as exc:
            logger.error("Failed to save attribution contract: %s", exc)
            raise
    
    def get_contract(self, platform: str) -> Optional[AttributionContract]:
        """Get attribution contract by platform."""
        try:
            data = self._tabular_service.get("attribution_contracts", f"contract#{platform}")
            if data:
                return AttributionContract.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to get attribution contract: %s", exc)
        return None
    
    def list_contracts(self) -> List[AttributionContract]:
        """List all attribution contracts."""
        contracts = []
        try:
            records = self._tabular_service.list_by_prefix("attribution_contracts", "contract#")
            for record in records:
                try:
                    contracts.append(AttributionContract.from_dict(record))
                except Exception as exc:
                    logger.warning("Failed to deserialize contract: %s", exc)
        except Exception as exc:
            logger.warning("Failed to list contracts: %s", exc)
        return contracts


class BudgetUsageRecord:
    """Tracks usage and soft limits per tenant/project/provider."""
    
    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        provider: str,
        metric: str,
        usage: float,
        soft_limit: Optional[float] = None,
        hard_limit: Optional[float] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.provider = provider
        self.metric = metric  # e.g., "tokens", "requests", "storage_gb"
        self.usage = usage
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.last_updated = datetime.now(timezone.utc).isoformat()
    
    def dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "provider": self.provider,
            "metric": self.metric,
            "usage": self.usage,
            "soft_limit": self.soft_limit,
            "hard_limit": self.hard_limit,
            "last_updated": self.last_updated,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> BudgetUsageRecord:
        return BudgetUsageRecord(
            tenant_id=data["tenant_id"],
            project_id=data["project_id"],
            provider=data["provider"],
            metric=data["metric"],
            usage=data["usage"],
            soft_limit=data.get("soft_limit"),
            hard_limit=data.get("hard_limit"),
        )


class BudgetService:
    """Manage usage tracking and budget limits via tabular store."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._tabular_service = TabularStoreService(context)
    
    def record_usage(self, record: BudgetUsageRecord) -> None:
        """Record usage for a provider/metric."""
        try:
            key = f"usage#{record.provider}#{record.metric}"
            self._tabular_service.upsert("budget_store", key, record.dict())
        except Exception as exc:
            logger.error("Failed to record usage: %s", exc)
            raise
    
    def get_usage(self, provider: str, metric: str) -> Optional[BudgetUsageRecord]:
        """Get usage record for provider/metric."""
        try:
            key = f"usage#{provider}#{metric}"
            data = self._tabular_service.get("budget_store", key)
            if data:
                return BudgetUsageRecord.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to get usage: %s", exc)
        return None
    
    def increment_usage(self, provider: str, metric: str, amount: float) -> BudgetUsageRecord:
        """Increment usage by amount."""
        record = self.get_usage(provider, metric)
        if not record:
            record = BudgetUsageRecord(
                tenant_id=self._context.tenant_id,
                project_id=self._context.project_id,
                provider=provider,
                metric=metric,
                usage=0.0,
            )
        record.usage += amount
        record.last_updated = datetime.now(timezone.utc).isoformat()
        self.record_usage(record)
        return record
    
    def check_soft_limit(self, provider: str, metric: str) -> bool:
        """Check if soft limit exceeded (warning)."""
        record = self.get_usage(provider, metric)
        if record and record.soft_limit and record.usage > record.soft_limit:
            return True
        return False
    
    def check_hard_limit(self, provider: str, metric: str) -> bool:
        """Check if hard limit exceeded (block)."""
        record = self.get_usage(provider, metric)
        if record and record.hard_limit and record.usage > record.hard_limit:
            return True
        return False
    
    def list_provider_usage(self, provider: str) -> List[BudgetUsageRecord]:
        """List all metrics for provider."""
        records = []
        try:
            prefix = f"usage#{provider}#"
            data_records = self._tabular_service.list_by_prefix("budget_store", prefix)
            for data in data_records:
                try:
                    records.append(BudgetUsageRecord.from_dict(data))
                except Exception as exc:
                    logger.warning("Failed to deserialize usage record: %s", exc)
        except Exception as exc:
            logger.warning("Failed to list usage: %s", exc)
        return records
