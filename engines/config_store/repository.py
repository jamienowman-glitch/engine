from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from engines.common.error_envelope import missing_route_error
from engines.common.identity import RequestContext
from engines.storage.routing_service import TabularStoreService


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ConfigRecord:
    def __init__(self, data: Dict[str, Any]):
        self.scope: str = data["scope"]
        self.identifier: str = data["identifier"]
        self.version: int = data["version"]
        self.values: Dict[str, Any] = data["values"]
        self.updated_at: str = data.get("updated_at")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "identifier": self.identifier,
            "version": self.version,
            "values": self.values,
            "updated_at": self.updated_at,
        }


class ConfigStoreRepository:
    TABLE_NAME = "config_store"

    def _tabular(self, ctx: RequestContext) -> TabularStoreService:
        try:
            return TabularStoreService(ctx, resource_kind="config_store")
        except RuntimeError as exc:
            raise missing_route_error(
                resource_kind="config_store",
                tenant_id=ctx.tenant_id,
                env=ctx.env,
            ) from exc

    def _key(self, ctx: RequestContext, scope: str, identifier: str) -> str:
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#config#{scope}#{identifier}"

    def get(self, ctx: RequestContext, scope: str, identifier: str) -> Optional[ConfigRecord]:
        data = self._tabular(ctx).get(self.TABLE_NAME, self._key(ctx, scope, identifier))
        if not data:
            return None
        return ConfigRecord(data)

    def save(self, ctx: RequestContext, scope: str, identifier: str, version: int, values: Dict[str, Any]) -> ConfigRecord:
        payload: Dict[str, Any] = {
            "scope": scope,
            "identifier": identifier,
            "version": version,
            "values": values,
            "updated_at": _now().isoformat(),
        }
        self._tabular(ctx).upsert(self.TABLE_NAME, self._key(ctx, scope, identifier), payload)
        return ConfigRecord(payload)
