"""Tests for Canvas Commands (Phase 2)."""
import pytest
from engines.canvas_commands.models import CommandEnvelope
from engines.canvas_commands.service import apply_command, repo
from engines.realtime.isolation import registry

@pytest.fixture(autouse=True)
def setup_data():
    registry.clear()
    registry.register_canvas("t_demo", "canvas-1")
    # Reset repo state
    repo._states.clear()
    repo._states["canvas-1"] = repo.get_state("canvas-1")
    repo._states["canvas-1"].rev = 10
    yield

@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_command_rev_mismatch():
    # Client thinks base is 9, server is 10
    cmd = CommandEnvelope(
        id="cmd-1",
        type="add_node",
        canvas_id="canvas-1",
        base_rev=9,
        idempotency_key="key-1"
    )
    
    result = await apply_command("t_demo", "u1", cmd)
    assert result.status == "conflict"
    assert result.current_rev == 10

@pytest.mark.anyio
async def test_command_success():
    # Client matches base 10
    cmd = CommandEnvelope(
        id="cmd-2",
        type="add_node",
        canvas_id="canvas-1",
        base_rev=10,
        idempotency_key="key-2"
    )
    
    result = await apply_command("t_demo", "u1", cmd)
    assert result.status == "applied"
    assert result.current_rev == 11

@pytest.mark.anyio
async def test_command_idempotency():
    cmd = CommandEnvelope(
        id="cmd-3",
        type="foo",
        canvas_id="canvas-1",
        base_rev=10,
        idempotency_key="key-idem"
    )
    
    # First attempt
    res1 = await apply_command("t_demo", "u1", cmd)
    assert res1.status == "applied"
    assert res1.current_rev == 11
    
    # Retry same key
    res2 = await apply_command("t_demo", "u1", cmd)
    assert res2.status == "applied"
    assert res2.current_rev == 11 # Rev didn't increment
    assert res2.reason == "Idempotent replay"

@pytest.mark.anyio
async def test_command_isolation():
    # Access unknown canvas
    cmd = CommandEnvelope(
        id="cmd-inf",
        type="hack",
        canvas_id="canvas-unknown",
        base_rev=0,
        idempotency_key="k"
    )
    
    # Should raise HTTPException (404)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await apply_command("t_demo", "u1", cmd)
    assert exc.value.status_code == 404
