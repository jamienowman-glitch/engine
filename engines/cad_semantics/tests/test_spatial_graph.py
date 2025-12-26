"""
Tests for CAD spatial graph construction and hashing.
"""

import pytest
from typing import Dict, Any
from engines.cad_semantics.models import SemanticElement, SemanticType, EdgeType
from engines.cad_semantics.graph import build_spatial_graph, bboxes_adjacent

def create_elem(id: str, type: SemanticType, x: float = 0.0, y: float = 0.0, z: float = 0.0, level_id: str = "L0") -> SemanticElement:
    return SemanticElement(
        id=id,
        cad_entity_id=f"cad_{id}",
        semantic_type=type,
        layer="Layer",
        geometry_ref={"x": x, "y": y, "z": z},
        level_id=level_id,
        elevation=z
    )

class TestSpatialGraphConstruction:
    
    def test_adjacency_logic(self):
        """Verify bboxes_adjacent respects tolerance."""
        e1 = create_elem("e1", SemanticType.WALL, x=0, y=0)
        e2 = create_elem("e2", SemanticType.WALL, x=0.05, y=0) # dist 0.05
        e3 = create_elem("e3", SemanticType.WALL, x=1.0, y=0)  # dist 1.0
        
        # Default tolerance is usually 0.1 in build_spatial_graph logic, 
        # but function defaults to 0.1 too.
        assert bboxes_adjacent(e1, e2, tolerance=0.1)
        assert not bboxes_adjacent(e1, e3, tolerance=0.1)

    def test_containment_edges(self):
        """Verify Room -> Level containment."""
        level = create_elem("l1", SemanticType.LEVEL, level_id="L1", z=3.0)
        # Level element usually has ID same as level_id or similar. 
        # In service.py, Level objects are created separately, but SemanticElements are also created.
        # graph.py looks for SemanticType.LEVEL elements.
        # Let's ensure level's .id matches what rooms point to, or .level_id match?
        # graph.py: 
        #   levels = [e for e in elements if e.semantic_type == SemanticType.LEVEL]
        #   for level in levels:
        #       for room in rooms:
        #           if room.level_id == level.level_id:
        
        room = create_elem("r1", SemanticType.ROOM, level_id="L1")
        
        # We need the level element's .level_id to match room.level_id
        # create_elem sets level_id="L1".
        
        graph = build_spatial_graph([level, room])
        
        edges = [e for e in graph.edges if e.edge_type == EdgeType.CONTAINED]
        assert len(edges) == 1
        assert edges[0].from_node_id == room.id
        assert edges[0].to_node_id == level.id

    def test_connectivity_edges(self):
        """Verify Door connects Rooms."""
        # Door on L1, Room1 on L1, Room2 on L1
        # Door at (0,0), Room1 at (0.5,0), Room2 at (-0.5,0)
        # tolerance in infer_door_connectivity is 2.0 (quite generous).
        
        door = create_elem("d1", SemanticType.DOOR, x=0, y=0, level_id="L1")
        r1 = create_elem("r1", SemanticType.ROOM, x=0.5, y=0, level_id="L1")
        r2 = create_elem("r2", SemanticType.ROOM, x=-0.5, y=0, level_id="L1")
        
        graph = build_spatial_graph([door, r1, r2])
        
        connect_edges = [e for e in graph.edges if e.edge_type == EdgeType.CONNECTS]
        # Should connect r1-r2 (or r2-r1, order depends on list iteration)
        assert len(connect_edges) >= 1
        edge = connect_edges[0]
        assert edge.meta["via_door"] == door.id
        assert {edge.from_node_id, edge.to_node_id} == {r1.id, r2.id}

    def test_graph_determinism_content_hash(self):
        """Verify hash depends on content, not just counts."""
        e1 = create_elem("e1", SemanticType.WALL, x=0, y=0)
        e2 = create_elem("e2", SemanticType.WALL, x=0.05, y=0)
        
        # Graph 1: Connected
        graph1 = build_spatial_graph([e1, e2])
        hash1 = graph1.graph_hash
        
        # Graph 2: Same elements, same connection -> Same hash
        graph2 = build_spatial_graph([e1, e2])
        assert graph2.graph_hash == hash1
        
        # Graph 3: Move e2 far away -> No connection
        e2_far = create_elem("e2", SemanticType.WALL, x=10.0, y=0)
        graph3 = build_spatial_graph([e1, e2_far])
        hash3 = graph3.graph_hash
        
        assert len(graph3.edges) == 0
        assert hash3 != hash1
        
        # Graph 4: Rename e1 -> e1b (same topology, different IDs)
        # Hash should change because IDs are part of hash
        e1b = create_elem("e1b", SemanticType.WALL, x=0, y=0)
        # We need e2 back close
        graph4 = build_spatial_graph([e1b, e2]) 
        assert graph4.graph_hash != hash1
