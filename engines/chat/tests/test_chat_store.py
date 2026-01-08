import pytest
from unittest.mock import patch
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.chat.store_service import ChatStoreServiceRejectOnMissing, MissingChatStoreRoute
from engines.event_spine.cloud_event_spine_store import SpineEvent
from engines.chat.service.routes import append_message, list_messages, ChatAppendRequest
from engines.identity.jwt_service import AuthContext
from engines.chat.contracts import Contact
from fastapi import HTTPException


class FakeAdapter:
    def __init__(self):
        self.events: List[SpineEvent] = []

    def append(self, event: SpineEvent, context: RequestContext) -> None:
        self.events.append(event)

    def list_events(
        self,
        tenant_id: str,
        run_id: str,
        event_type: Optional[str] = None,
        after_event_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SpineEvent]:
        filtered = [e for e in self.events if e.run_id == run_id and (event_type is None or e.event_type == event_type)]
        if after_event_id:
            for idx, ev in enumerate(filtered):
                if ev.event_id == after_event_id:
                    return filtered[idx + 1 : idx + 1 + limit]
            return []
        return filtered[:limit]


@pytest.fixture
def fake_context():
    return RequestContext(
        tenant_id="t_test",
        env="dev",
        mode="saas",
        project_id="proj1",
        request_id="req1",
        user_id="user1",
    )


def test_append_and_list_persists_across_service_instances(fake_context):
    adapter = FakeAdapter()
    with patch("engines.chat.store_service.ChatStoreServiceRejectOnMissing._resolve_adapter_or_raise", return_value=adapter):
        svc1 = ChatStoreServiceRejectOnMissing(fake_context)
        record = svc1.append_message(thread_id="thread-1", text="hello", role="user", sender_id="user1")
        assert record.cursor

        # Simulate restart: new service uses same adapter
        svc2 = ChatStoreServiceRejectOnMissing(fake_context)
        messages = svc2.list_messages(thread_id="thread-1")
        assert len(messages) == 1
        assert messages[0].cursor == record.cursor


def test_invalid_cursor_raises_410(fake_context):
    adapter = FakeAdapter()
    with patch("engines.chat.store_service.ChatStoreServiceRejectOnMissing._resolve_adapter_or_raise", return_value=adapter):
        svc = ChatStoreServiceRejectOnMissing(fake_context)
        with pytest.raises(HTTPException) as exc_info:
            svc.list_messages(thread_id="thread-1", after_cursor="bad_cursor")
        assert exc_info.value.status_code == 410
        assert exc_info.value.detail["error"]["code"] == "chat.cursor_invalid"


def test_missing_route_returns_503(fake_context):
    with patch("engines.chat.store_service.routing_registry") as mock_registry:
        mock_registry.return_value.get_route.return_value = None
        with pytest.raises(Exception) as exc_info:
            ChatStoreServiceRejectOnMissing(fake_context)
        assert isinstance(exc_info.value, MissingChatStoreRoute)


def test_append_and_list_routes(fake_context):
    adapter = FakeAdapter()
    with patch("engines.chat.store_service.ChatStoreServiceRejectOnMissing._resolve_adapter_or_raise", return_value=adapter):
        auth = AuthContext(
            user_id="user1",
            email="u@example.com",
            tenant_ids=[fake_context.tenant_id],
            default_tenant_id=fake_context.tenant_id,
            role_map={fake_context.tenant_id: "owner"},
        )
        contact = Contact(id="user1")
        msg_out = append_message(
            thread_id="thread-x",
            payload=ChatAppendRequest(text="hi", role="user"),
            context=fake_context,
            auth=auth,
        )
        assert msg_out.cursor

        response = list_messages(thread_id="thread-x", cursor=None, limit=100, context=fake_context, auth=auth)
        assert len(response.messages) == 1
        assert response.messages[0].text == "hi"
