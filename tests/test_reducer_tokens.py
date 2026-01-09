"""Tests for Canvas Reducer Tokens (EN-03)."""
import pytest
from engines.canvas_reducer import CanvasReducer, CanvasState

def test_set_token():
    state = CanvasState()

    # Create token
    args = {
        "id": "t1",
        "node_id": "n1",
        "value": 42,
        "status": "active"
    }

    CanvasReducer.apply(state, "set_token", args)

    assert "t1" in state.tokens
    token = state.tokens["t1"]
    assert token.node_id == "n1"
    assert token.value == 42
    assert token.status == "active"

    # Update token
    args_update = {
        "id": "t1",
        "value": 100
    }

    CanvasReducer.apply(state, "set_token", args_update)
    token = state.tokens["t1"]
    assert token.value == 100
    assert token.node_id == "n1" # preserved

def test_delete_token():
    state = CanvasState()
    CanvasReducer.apply(state, "set_token", {"id": "t1", "node_id": "n1"})
    assert "t1" in state.tokens

    CanvasReducer.apply(state, "delete_token", {"id": "t1"})
    assert "t1" not in state.tokens
