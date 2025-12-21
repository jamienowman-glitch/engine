from __future__ import annotations

from typing import Dict, Optional, Protocol

from engines.billing.models import SubscriptionRecord


class SubscriptionRepository(Protocol):
    def upsert(self, record: SubscriptionRecord) -> SubscriptionRecord: ...
    def get(self, tenant_id: str) -> Optional[SubscriptionRecord]: ...


class InMemorySubscriptionRepository:
    def __init__(self) -> None:
        self._items: Dict[str, SubscriptionRecord] = {}

    def upsert(self, record: SubscriptionRecord) -> SubscriptionRecord:
        self._items[record.tenant_id] = record
        return record

    def get(self, tenant_id: str) -> Optional[SubscriptionRecord]:
        return self._items.get(tenant_id)
