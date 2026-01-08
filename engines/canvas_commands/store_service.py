from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from engines.common.identity import RequestContext
from engines.common.error_envelope import missing_route_error
from engines.storage.routing_service import TabularStoreService

logger = logging.getLogger(__name__)


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


class CanvasCommandStoreService:
    """Routing-backed adapter for canvas_command_store resource."""

    HEAD_TABLE = "canvas_heads"
    COMMAND_TABLE = "canvas_commands"
    IDEMPOTENCY_TABLE = "canvas_idempotency"

    def __init__(self, context: RequestContext) -> None:
        self.context = context
        self._adapter = self._resolve_adapter()

    def _resolve_adapter(self) -> TabularStoreService:
        try:
            return TabularStoreService(self.context, resource_kind="canvas_command_store")
        except RuntimeError as exc:
            logger.error("Canvas command store missing: %s", exc)
            raise missing_route_error(
                resource_kind="canvas_command_store",
                tenant_id=self.context.tenant_id,
                env=self.context.env,
            ) from exc

    def _head_key(self, canvas_id: str) -> str:
        return f"{self.context.tenant_id}#{self.context.mode}#{self.context.env}#head#{canvas_id}"

    def _command_key(self, canvas_id: str, revision: int) -> str:
        return f"{self.context.tenant_id}#{self.context.mode}#{self.context.env}#command#{canvas_id}#rev#{revision:010d}"

    def _idempotency_key(self, canvas_id: str, idempotency_key: str) -> str:
        return f"{self.context.tenant_id}#{self.context.mode}#{self.context.env}#idem#{canvas_id}#{idempotency_key}"

    def get_head_revision(self, canvas_id: str) -> int:
        data = self._adapter.get(self.HEAD_TABLE, self._head_key(canvas_id))
        if data and "head_rev" in data:
            return int(data["head_rev"])
        return 0

    def check_idempotency(self, canvas_id: str, idempotency_key: Optional[str]) -> Optional[Dict[str, Any]]:
        if not idempotency_key:
            return None
        data = self._adapter.get(self.IDEMPOTENCY_TABLE, self._idempotency_key(canvas_id, idempotency_key))
        return data

    def append_command(
        self,
        canvas_id: str,
        command_id: str,
        idempotency_key: Optional[str],
        base_rev: int,
        command_type: str,
        command_args: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, Any]:
        head_rev = self.get_head_revision(canvas_id)
        if head_rev != base_rev:
            raise ValueError("base_rev mismatch")

        new_rev = head_rev + 1
        event_id = f"{canvas_id}:{new_rev}"
        timestamp = _now()
        command_record = {
            "canvas_id": canvas_id,
            "command_id": command_id,
            "revision": new_rev,
            "command_args": command_args,
            "type": command_type,
            "event_id": event_id,
            "timestamp": timestamp,
            "user_id": user_id,
            "base_rev": base_rev,
        }
        self._adapter.upsert(
            self.COMMAND_TABLE,
            self._command_key(canvas_id, new_rev),
            command_record,
        )
        self._adapter.upsert(
            self.HEAD_TABLE,
            self._head_key(canvas_id),
            {"canvas_id": canvas_id, "head_rev": new_rev, "updated_at": timestamp},
        )
        if idempotency_key:
            self._adapter.upsert(
                self.IDEMPOTENCY_TABLE,
                self._idempotency_key(canvas_id, idempotency_key),
                {
                    "command_id": command_id,
                    "canvas_id": canvas_id,
                    "revision": new_rev,
                    "event_id": event_id,
                    "timestamp": timestamp,
                },
            )
        return command_record

    def list_commands_since(self, canvas_id: str, since_rev: int) -> List[Dict[str, Any]]:
        prefix = f"{self.context.tenant_id}#{self.context.mode}#{self.context.env}#command#{canvas_id}#rev#"
        records = self._adapter.list_by_prefix(self.COMMAND_TABLE, prefix)
        sorted_records = sorted(records or [], key=lambda rec: rec.get("revision", 0))
        return [rec for rec in sorted_records if rec.get("revision", 0) > since_rev]
