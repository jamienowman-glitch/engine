"""
Spatial Graph - Build and analyze spatial relationships between semantic elements.

Implements:
- Adjacency detection (touching elements)
- Containment relationships (rooms within levels)
- Connectivity (doors connecting rooms)
- Graph determinism and hashing
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Set, Tuple

from engines.cad_semantics.models import (
    EdgeType,
    SemanticElement,
    SemanticType,
    SpatialGraph,
    SpatialGraphEdge,
    SpatialGraphNode,
)


def distance_3d(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    """Compute distance between two points."""
    x = (p1.get("x", 0) - p2.get("x", 0)) ** 2
    y = (p1.get("y", 0) - p2.get("y", 0)) ** 2
    z = (p1.get("z", 0) - p2.get("z", 0)) ** 2
    return (x + y + z) ** 0.5


def bboxes_adjacent(elem1: SemanticElement, elem2: SemanticElement, tolerance: float = 0.1) -> bool:
    """
    Check if two element bboxes are adjacent (touching or very close).
    Simplified: check if centroids are close.
    """
    geo1 = elem1.geometry_ref
    geo2 = elem2.geometry_ref
    
    c1 = {"x": geo1.get("x", 0), "y": geo1.get("y", 0), "z": geo1.get("z", 0)}
    c2 = {"x": geo2.get("x", 0), "y": geo2.get("y", 0), "z": geo2.get("z", 0)}
    
    dist = distance_3d(c1, c2)
    return dist <= tolerance


def infer_room_containment(rooms: List[SemanticElement], level_id: str) -> List[Tuple[str, str]]:
    """
    Infer which rooms are on which levels (simple heuristic: same level_id).
    Returns list of (room_id, level_id) containments.
    """
    containments = []
    for room in rooms:
        if room.level_id == level_id:
            containments.append((room.id, level_id))
    return containments


def infer_door_connectivity(
    doors: List[SemanticElement], rooms: List[SemanticElement]
) -> List[Tuple[str, str]]:
    """
    Infer which rooms a door connects.
    Simplified: doors connect rooms with similar level_id and adjacent geometry.
    Returns list of (door_id, room_id) edges.
    """
    edges = []
    for door in doors:
        for room in rooms:
            if door.level_id == room.level_id and bboxes_adjacent(door, room, tolerance=2.0):
                edges.append((door.id, room.id))
    return edges


def build_spatial_graph(elements: List[SemanticElement]) -> SpatialGraph:
    """
    Build spatial graph from semantic elements.
    Includes adjacency, containment, and connectivity edges.
    """
    graph = SpatialGraph()
    
    # Create nodes for each element
    node_map: Dict[str, SpatialGraphNode] = {}
    for elem in elements:
        node = SpatialGraphNode(
            node_id=elem.id,
            semantic_element_id=elem.id,
            semantic_type=elem.semantic_type,
        )
        graph.nodes.append(node)
        node_map[elem.id] = node
    
    # Find adjacency edges (touching elements)
    for i, elem1 in enumerate(elements):
        for elem2 in elements[i + 1 :]:
            if bboxes_adjacent(elem1, elem2, tolerance=0.1):
                edge = SpatialGraphEdge(
                    from_node_id=elem1.id,
                    to_node_id=elem2.id,
                    edge_type=EdgeType.ADJACENT,
                )
                graph.edges.append(edge)
                graph.adjacency_edge_count += 1
    
    # Find containment edges (rooms on levels)
    rooms = [e for e in elements if e.semantic_type == SemanticType.ROOM]
    levels = [e for e in elements if e.semantic_type == SemanticType.LEVEL]
    
    for level in levels:
        for room in rooms:
            if room.level_id == level.level_id:
                edge = SpatialGraphEdge(
                    from_node_id=room.id,
                    to_node_id=level.id,
                    edge_type=EdgeType.CONTAINED,
                )
                graph.edges.append(edge)
                graph.containment_edge_count += 1
    
    # Find connectivity edges (doors connect rooms)
    doors = [e for e in elements if e.semantic_type == SemanticType.DOOR]
    
    for door in doors:
        connected_rooms = []
        for room in rooms:
            if door.level_id == room.level_id and bboxes_adjacent(door, room, tolerance=2.0):
                connected_rooms.append(room.id)
        
        # If door touches 2+ rooms, create connectivity edges
        for i, room_id1 in enumerate(connected_rooms):
            for room_id2 in connected_rooms[i + 1 :]:
                edge = SpatialGraphEdge(
                    from_node_id=room_id1,
                    to_node_id=room_id2,
                    edge_type=EdgeType.CONNECTS,
                    meta={"via_door": door.id},
                )
                graph.edges.append(edge)
                graph.connectivity_edge_count += 1
    
    # Compute graph hash (deterministic and content-based)
    # Sort nodes and edges for consistent hashing
    sorted_node_ids = sorted(n.node_id for n in graph.nodes)
    
    # Edges sorted by (from, to, type)
    sorted_edge_keys = sorted(
        f"{e.from_node_id}:{e.to_node_id}:{e.edge_type.value}" 
        for e in graph.edges
    )
    
    # Combined representation
    nodes_str = ",".join(sorted_node_ids)
    edges_str = ",".join(sorted_edge_keys)
    graph_repr = f"nodes:[{nodes_str}]|edges:[{edges_str}]"
    
    graph.graph_hash = hashlib.sha256(graph_repr.encode()).hexdigest()[:16]
    
    return graph


def validate_graph_connectivity(graph: SpatialGraph) -> Tuple[bool, List[str]]:
    """
    Validate graph structure.
    Returns (is_valid, list of issues).
    """
    issues = []
    
    # Check that all edge endpoints exist
    node_ids = {n.node_id for n in graph.nodes}
    for edge in graph.edges:
        if edge.from_node_id not in node_ids:
            issues.append(f"Edge from unknown node: {edge.from_node_id}")
        if edge.to_node_id not in node_ids:
            issues.append(f"Edge to unknown node: {edge.to_node_id}")
    
    # Check for isolated nodes (optional warning)
    edge_nodes = set()
    for edge in graph.edges:
        edge_nodes.add(edge.from_node_id)
        edge_nodes.add(edge.to_node_id)
    
    isolated = node_ids - edge_nodes
    if isolated:
        # Not an error, just a note
        pass
    
    return len(issues) == 0, issues
