"""Tests for Canvas Reducer (EN-02)."""
import pytest
from engines.canvas_reducer import CanvasReducer, CanvasState, NodeState, EdgeState

def test_upsert_node():
    state = CanvasState()

    # Create new node
    args = {
        "id": "node-1",
        "type": "process",
        "data": {"label": "Start"},
        "position": {"x": 100, "y": 200}
    }

    CanvasReducer.apply(state, "upsert_node", args)

    assert "node-1" in state.nodes
    node = state.nodes["node-1"]
    assert node.type == "process"
    assert node.data["label"] == "Start"
    assert node.position["x"] == 100

    # Update existing node
    args_update = {
        "id": "node-1",
        "data": {"label": "Updated"},
        "position": {"x": 150} # Partial update? Reducer logic replaces dict if provided, or merges?
                               # My implementation: node.position = args["position"] (replaces)
    }

    CanvasReducer.apply(state, "upsert_node", args_update)
    node = state.nodes["node-1"]
    assert node.data["label"] == "Updated" # merged? No, update() was called on data dict.
    assert node.position["x"] == 150
    assert "y" not in node.position # Replaced whole dict

def test_upsert_edge():
    state = CanvasState()

    # Create edge
    args = {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2",
        "data": {"weight": 1}
    }

    CanvasReducer.apply(state, "upsert_edge", args)

    assert "edge-1" in state.edges
    edge = state.edges["edge-1"]
    assert edge.source == "node-1"
    assert edge.target == "node-2"

    # Update edge
    args_update = {
        "id": "edge-1",
        "data": {"weight": 2}
    }

    CanvasReducer.apply(state, "upsert_edge", args_update)
    edge = state.edges["edge-1"]
    assert edge.data["weight"] == 2
    assert edge.source == "node-1" # preserved

def test_delete_node_cascades_edges():
    state = CanvasState()

    # Setup
    CanvasReducer.apply(state, "upsert_node", {"id": "n1"})
    CanvasReducer.apply(state, "upsert_node", {"id": "n2"})
    CanvasReducer.apply(state, "upsert_edge", {"id": "e1", "source": "n1", "target": "n2"})

    assert "n1" in state.nodes
    assert "e1" in state.edges

    # Delete n1
    CanvasReducer.apply(state, "delete_node", {"id": "n1"})

    assert "n1" not in state.nodes
    assert "e1" not in state.edges # Cascaded
