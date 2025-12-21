"""Tests for Canonical Realtime Contracts."""
import pytest
from datetime import datetime
from engines.realtime.contracts import (
    StreamEvent, RoutingKeys, EventIds, ActorType, from_legacy_message
)
from engines.chat.contracts import Message, Contact, ChatScope

def test_stream_event_minimal():
    """Verify minimal valid StreamEvent."""
    routing = RoutingKeys(
        tenant_id="t_demo",
        env="dev",
        actor_id="user-123",
        actor_type=ActorType.HUMAN
    )
    event = StreamEvent(
        type="test_ping",
        routing=routing,
        data={"foo": "bar"}
    )
    assert event.v == 1
    assert event.type == "test_ping"
    assert event.routing.tenant_id == "t_demo"
    assert event.event_id is not None
    assert event.ts is not None

def test_routing_validation():
    """Verify routing key validation patterns."""
    # Invalid tenant format
    with pytest.raises(ValueError):
        RoutingKeys(
            tenant_id="bad-tenant", # Missing t_
            env="dev",
            actor_id="u1",
            actor_type=ActorType.HUMAN
        )
    
    # Valid
    rk = RoutingKeys(
        tenant_id="t_valid_1",
        env="prod",
        actor_id="u1",
        actor_type=ActorType.HUMAN
    )
    assert rk.tenant_id == "t_valid_1"

def test_legacy_message_conversion():
    """Verify from_legacy_message adapter."""
    msg = Message(
        id="msg-1",
        thread_id="th-1",
        sender=Contact(id="u-legacy"),
        text="Hello World",
        role="user",
        scope=ChatScope(app="app-1")
    )
    
    event = from_legacy_message(msg, tenant_id="t_legacy", env="dev", request_id="req-1")
    
    assert event.type == "user_message"
    assert event.routing.tenant_id == "t_legacy"
    assert event.routing.thread_id == "th-1"
    assert event.routing.app_id == "app-1"
    assert event.ids.request_id == "req-1"
    assert event.data["text"] == "Hello World"
    assert event.meta.last_event_id == event.event_id


def test_legacy_message_trace_id():
    msg = Message(
        id="msg-3",
        thread_id="th-3",
        sender=Contact(id="u-legacy"),
        text="Trace me",
        role="user"
    )

    event = from_legacy_message(
        msg,
        tenant_id="t_legacy",
        env="dev",
        trace_id="trace-007"
    )

    assert event.trace_id == "trace-007"

def test_legacy_json_unwrapping():
    """Verify checking for structured JSON inside legacy text."""
    import json
    inner = {
        "type": "token_chunk",
        "data": {"delta": "Hi"},
        "request_id": "req-internal"
    }
    msg = Message(
        id="msg-2",
        thread_id="th-2",
        sender=Contact(id="agent-1"),
        text=json.dumps(inner),
        role="agent"
    )
    
    event = from_legacy_message(msg, tenant_id="t_legacy", env="dev")
    
    assert event.type == "token_chunk"
    assert event.ids.request_id == "req-internal"
    assert event.data["delta"] == "Hi"
