"""Tests for Tenant Isolation."""
import pytest
from fastapi import HTTPException
from engines.common.identity import RequestContext
from engines.realtime.contracts import RoutingKeys, ActorType
from engines.realtime.isolation import (
    InMemoryResourceRegistry,
    get_registry,
    set_registry,
    validate_routing,
    verify_thread_access,
    verify_canvas_access,
)

@pytest.fixture(autouse=True)
def clean_registry():
    set_registry(InMemoryResourceRegistry())
    get_registry().clear()
    yield

def test_validate_routing_happy():
    ctx = RequestContext(tenant_id="t_1", env="dev")
    routing = RoutingKeys(
        tenant_id="t_1", env="dev", actor_id="u1", actor_type=ActorType.HUMAN
    )
    # Should not raise
    validate_routing(ctx, routing)

def test_validate_routing_mismatch():
    ctx = RequestContext(tenant_id="t_1", env="dev")
    
    # Tenant mismatch
    with pytest.raises(HTTPException) as exc:
        validate_routing(ctx, RoutingKeys(
            tenant_id="t_2", env="dev", actor_id="u1", actor_type=ActorType.HUMAN
        ))
    assert exc.value.status_code == 403
    
    # Env mismatch
    with pytest.raises(HTTPException) as exc:
        validate_routing(ctx, RoutingKeys(
            tenant_id="t_1", env="prod", actor_id="u1", actor_type=ActorType.HUMAN
        ))
    assert exc.value.status_code == 403

def test_verify_thread_access_strict():
    # Setup registry
    get_registry().register_thread("t_A", "thread-A1")
    get_registry().register_thread("t_B", "thread-B1")
    
    # Happy path
    verify_thread_access("t_A", "thread-A1")
    
    # Access other tenant's thread -> 404 (don't leak existence)
    with pytest.raises(HTTPException) as exc:
        verify_thread_access("t_A", "thread-B1")
    assert exc.value.status_code == 404
    
    # Access unknown thread -> 404
    with pytest.raises(HTTPException) as exc:
        verify_thread_access("t_A", "thread-unknown")
    assert exc.value.status_code == 404

def test_verify_canvas_access_strict():
    get_registry().register_canvas("t_A", "canvas-A1")
    
    verify_canvas_access("t_A", "canvas-A1")
    
    with pytest.raises(HTTPException) as exc:
        verify_canvas_access("t_B", "canvas-A1")
    assert exc.value.status_code == 404
