"""Chat store service (routing-only, durable) for append/list/snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from engines.common.identity import RequestContext
from engines.common.error_envelope import missing_route_error, cursor_invalid_error
from engines.routing.registry import routing_registry, MissingRoutingConfig
from engines.event_spine.cloud_event_spine_store import (
    SpineEvent,
    FirestoreEventSpineStore,
    DynamoDBEventSpineStore,
    CosmosEventSpineStore,
)


class MissingChatStoreRoute(Exception):
    """Raised when chat_store route is missing."""

    def __init__(self, context: RequestContext, status_code: int = 503):
        self.error_code = "chat_store.missing_route"
        self.status_code = status_code
        self.message = (
            f"Chat store route not configured for tenant={context.tenant_id}, env={context.env}. "
            "Configure routing entry with resource_kind=chat_store."
        )
        super().__init__(self.message)


@dataclass
class ChatMessageRecord:
    message_id: str
    thread_id: str
    text: str
    role: str
    sender_id: str
    cursor: str
    timestamp: str


class ChatStoreServiceRejectOnMissing:
    """Chat store resolved via routing registry. No fallbacks."""

    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._adapter = self._resolve_adapter_or_raise()

    def _resolve_adapter_or_raise(self):
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="chat_store",
                tenant_id=self._context.tenant_id,
                env=self._context.env,
                project_id=self._context.project_id,
            )
            if not route:
                raise MissingChatStoreRoute(self._context)

            backend_type = (route.backend_type or "").lower()
            config = route.config or {}

            if backend_type == "firestore":
                project = config.get("project")
                return FirestoreEventSpineStore(project=project)
            if backend_type == "dynamodb":
                table_name = config.get("table_name", "chat_store")
                region = config.get("region", "us-west-2")
                return DynamoDBEventSpineStore(table_name=table_name, region=region)
            if backend_type == "cosmos":
                endpoint = config.get("endpoint")
                key = config.get("key")
                database = config.get("database", "chat_store")
                return CosmosEventSpineStore(endpoint=endpoint, key=key, database=database)

            raise MissingChatStoreRoute(self._context)
        except MissingRoutingConfig:
            raise MissingChatStoreRoute(self._context)

    def append_message(self, thread_id: str, text: str, role: str, sender_id: str) -> ChatMessageRecord:
        """Append chat message durably."""
        event = SpineEvent(
            tenant_id=self._context.tenant_id,
            mode=self._context.mode or self._context.env or "unknown",
            event_type="chat_message",
            source="chat_service",
            run_id=thread_id,
            payload={"text": text, "role": role, "sender_id": sender_id},
            user_id=sender_id,
            surface_id=self._context.surface_id,
            project_id=self._context.project_id,
            trace_id=self._context.trace_id or self._context.request_id,
        )
        self._adapter.append(event, self._context)
        return ChatMessageRecord(
            message_id=event.event_id,
            thread_id=thread_id,
            text=text,
            role=role,
            sender_id=sender_id,
            cursor=event.event_id,
            timestamp=event.timestamp,
        )

    def _list_events(
        self,
        thread_id: str,
        after_cursor: Optional[str],
        limit: int,
    ) -> List[SpineEvent]:
        return self._adapter.list_events(
            tenant_id=self._context.tenant_id,
            run_id=thread_id,
            event_type="chat_message",
            after_event_id=after_cursor,
            limit=limit,
        )

    def list_messages(
        self,
        thread_id: str,
        after_cursor: Optional[str] = None,
        limit: int = 100,
    ) -> List[ChatMessageRecord]:
        """List messages after cursor (inclusive start after)."""
        events = self._list_events(thread_id, after_cursor, limit)
        if after_cursor and (events is None or len(events) == 0):
            latest = self._latest_cursor_direct(thread_id)
            if latest != after_cursor:
                raise cursor_invalid_error(after_cursor, domain="chat")

        result: List[ChatMessageRecord] = []
        for ev in events or []:
            payload = ev.payload or {}
            result.append(
                ChatMessageRecord(
                    message_id=ev.event_id,
                    thread_id=thread_id,
                    text=payload.get("text", ""),
                    role=payload.get("role", "user"),
                    sender_id=payload.get("sender_id", ev.user_id or ""),
                    cursor=ev.event_id,
                    timestamp=ev.timestamp,
                )
            )
        return result

    def latest_cursor(self, thread_id: str) -> Optional[str]:
        return self._latest_cursor_direct(thread_id)

    def _latest_cursor_direct(self, thread_id: str) -> Optional[str]:
        events = self._list_events(thread_id=thread_id, after_cursor=None, limit=1000)
        if not events:
            return None
        return events[-1].event_id


def chat_store_or_503(context: RequestContext) -> ChatStoreServiceRejectOnMissing:
    """Helper to construct chat store or raise HTTPException 503 envelope."""
    try:
        return ChatStoreServiceRejectOnMissing(context)
    except MissingChatStoreRoute as exc:
        raise missing_route_error(
            resource_kind="chat_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=exc.status_code,
        )
