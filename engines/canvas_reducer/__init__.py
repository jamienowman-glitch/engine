"""Canvas Reducer - Deterministic State Application (EN-02/EN-03).

Responsible for applying commands to state deterministically.
Pure logic, no side effects (except logging).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

class NodeState(BaseModel):
    """Canonical representation of a node in state."""
    id: str
    type: str = "node"
    data: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, float]] = None

    model_config = ConfigDict(extra="allow")

class EdgeState(BaseModel):
    """Canonical representation of an edge in state."""
    id: str
    source: str
    target: str
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

class TokenState(BaseModel):
    """Token state for simulation/execution."""
    id: str
    node_id: str
    value: Any = None
    status: str = "active"

    model_config = ConfigDict(extra="allow")

class CanvasState(BaseModel):
    """Full canvas state model."""
    nodes: Dict[str, NodeState] = Field(default_factory=dict)
    edges: Dict[str, EdgeState] = Field(default_factory=dict)
    tokens: Dict[str, TokenState] = Field(default_factory=dict)
    global_values: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

class ReducerContext(BaseModel):
    """Context for reduction (user info, time, etc)."""
    user_id: Optional[str] = None
    timestamp: float = 0.0

class CanvasReducer:
    """Applies commands to CanvasState."""

    @staticmethod
    def apply(state: CanvasState, command_type: str, args: Dict[str, Any], context: Optional[ReducerContext] = None) -> CanvasState:
        """Apply a single command to state, returning new state (or modifying in place).

        For performance, we might modify in place if safe, but conceptual model is functional.
        """
        # We'll modify in place for now as Pydantic models are mutable by default
        # and deep copying whole state on every op is expensive.

        method_name = f"_apply_{command_type}"
        handler = getattr(CanvasReducer, method_name, None)

        if handler:
            try:
                handler(state, args, context)
            except Exception as exc:
                logger.error(f"Reducer failed to apply {command_type}: {exc}")
                # We do not raise, we just log and ignore invalid commands to preserve stability?
                # Or should we raise? The requirements say "minimal deterministic apply logic".
                # If a command is invalid (e.g. missing fields), we probably shouldn't crash the state.
                pass
        else:
            logger.warning(f"Unknown command type: {command_type}")

        return state

    @staticmethod
    def _apply_upsert_node(state: CanvasState, args: Dict[str, Any], context: Optional[ReducerContext]):
        node_id = args.get("id")
        if not node_id:
            return

        # Merge or create
        if node_id in state.nodes:
            node = state.nodes[node_id]
            # Update fields
            if "data" in args:
                node.data.update(args["data"])
            if "position" in args:
                node.position = args["position"]
            if "type" in args:
                node.type = args["type"]
            # Extra fields
            for k, v in args.items():
                if k not in ["id", "data", "position", "type"]:
                    setattr(node, k, v) # This might fail if strict, but we used extra="allow"
        else:
            # Create new
            state.nodes[node_id] = NodeState(**args)

    @staticmethod
    def _apply_upsert_edge(state: CanvasState, args: Dict[str, Any], context: Optional[ReducerContext]):
        edge_id = args.get("id")
        if not edge_id:
            return

        # Basic validation
        source = args.get("source")
        target = args.get("target")

        if edge_id in state.edges:
            edge = state.edges[edge_id]
            if "data" in args:
                edge.data.update(args["data"])
            if source:
                edge.source = source
            if target:
                edge.target = target
        else:
            if not source or not target:
                return # Cannot create edge without source/target
            state.edges[edge_id] = EdgeState(**args)

    @staticmethod
    def _apply_delete_node(state: CanvasState, args: Dict[str, Any], context: Optional[ReducerContext]):
        node_id = args.get("id")
        if node_id and node_id in state.nodes:
            del state.nodes[node_id]
            # Cascade delete edges? usually yes.
            # Find edges connected to this node
            edges_to_remove = []
            for eid, edge in state.edges.items():
                if edge.source == node_id or edge.target == node_id:
                    edges_to_remove.append(eid)
            for eid in edges_to_remove:
                del state.edges[eid]

    @staticmethod
    def _apply_delete_edge(state: CanvasState, args: Dict[str, Any], context: Optional[ReducerContext]):
        edge_id = args.get("id")
        if edge_id and edge_id in state.edges:
            del state.edges[edge_id]

    @staticmethod
    def _apply_set_token(state: CanvasState, args: Dict[str, Any], context: Optional[ReducerContext]):
        """EN-03: Implement set_token in reducer."""
        token_id = args.get("id")
        if not token_id:
            return

        if token_id in state.tokens:
            token = state.tokens[token_id]
            if "value" in args:
                token.value = args["value"]
            if "status" in args:
                token.status = args["status"]
            if "node_id" in args:
                token.node_id = args["node_id"]
        else:
            node_id = args.get("node_id")
            if not node_id:
                return # Cannot create token without node_id
            state.tokens[token_id] = TokenState(**args)

    @staticmethod
    def _apply_delete_token(state: CanvasState, args: Dict[str, Any], context: Optional[ReducerContext]):
        token_id = args.get("id")
        if token_id and token_id in state.tokens:
            del state.tokens[token_id]
