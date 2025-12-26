"""
Tests for topology healing module.
"""

import pytest
from engines.cad_ingest.topology_heal import (
    heal_topology,
    distance_3d,
    vector_equal,
    normalize_polygon_winding,
    close_gaps_in_polyline,
    deduplicate_vertices,
    heal_polyline_geometry,
    remove_duplicate_entities
)
from engines.cad_ingest.models import Entity, EntityType, Vector3, BoundingBox, HealingActionKind

class TestTopologyPrimitives:
    """Test low-level healing primitives."""

    def test_distance_and_equality(self):
        v1 = Vector3(x=0, y=0, z=0)
        v2 = Vector3(x=0.0005, y=0, z=0)
        
        assert distance_3d(v1, v2) == 0.0005
        assert vector_equal(v1, v2, tolerance=0.001) is True
        assert vector_equal(v1, v2, tolerance=0.0001) is False

    def test_deduplicate_vertices(self):
        """Test removing consecutive duplicates."""
        verts = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=0.0001, y=0, z=0),  # Duplicate within tol
            Vector3(x=1, y=1, z=0),
        ]
        
        cleaned, actions = deduplicate_vertices(verts, tolerance=0.001)
        
        assert len(cleaned) == 2
        assert cleaned[0].x == 0
        assert cleaned[1].x == 1
        assert len(actions) == 1
        assert "deduped_1_vertices" in actions[0]

    def test_close_gaps_in_polyline(self):
        """Test closing endpoint gaps."""
        verts = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=1, y=1, z=0),
            Vector3(x=0.0005, y=0, z=0),  # Close to start
        ]
        
        closed, actions = close_gaps_in_polyline(verts, tolerance=0.001)
        
        # Last point should snap to first
        assert closed[-1].x == 0
        assert closed[-1].y == 0
        assert len(actions) == 1
        assert "closed_endpoint_gap" in actions[0]

    def test_normalize_winding(self):
        """Test polygon winding normalization (CCW)."""
        # Clockwise triangle
        cw_triangle = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=0, y=1, z=0),
            Vector3(x=1, y=0, z=0),
        ]
        
        normalized = normalize_polygon_winding(cw_triangle)
        
        # Should be reversed
        assert normalized[0] == cw_triangle[2]
        assert normalized[1] == cw_triangle[1]
        assert normalized[2] == cw_triangle[0]
        
        # CCW triangle (already correct)
        ccw_triangle = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=0, y=1, z=0),
        ]
        assert normalize_polygon_winding(ccw_triangle) == ccw_triangle


class TestHealTopology:
    """Test high-level healing pipeline."""

    @pytest.fixture
    def sample_entities(self):
        bbox = BoundingBox(min=Vector3(x=0, y=0, z=0), max=Vector3(x=1, y=1, z=0))
        return [
            Entity(
                id="e1",
                type=EntityType.POLYLINE,
                layer="0",
                geometry={
                    "vertices": [
                        {"x": 0, "y": 0, "z": 0},
                        {"x": 0.0001, "y": 0, "z": 0},  # Duplicate
                        {"x": 1, "y": 0, "z": 0},
                    ],
                    "closed": False
                },
                bbox=bbox
            ),
            Entity(
                id="e2",
                type=EntityType.SOLID,  # Box
                layer="0",
                geometry={
                    "x": 0, "y": 0, "z": 0,
                    "width": 1, "height": 1, "length": 1
                },
                bbox=bbox
            )
        ]

    def test_heal_entity_geometry(self, sample_entities):
        """Test healing within entity geometry."""
        healed, actions = heal_topology(sample_entities, tolerance=0.001)
        
        # e1 should have deduped vertices
        e1 = healed[0]
        assert len(e1.geometry["vertices"]) == 2
        
        # e2 (SOLID) should be untouched
        e2 = healed[1]
        assert e2.geometry == sample_entities[1].geometry
        
        # Should have actions recorded
        assert len(actions) > 0
        assert getattr(actions[0], "kind", None) or actions[0].kind == HealingActionKind.VERTEX_DEDUP

    def test_remove_duplicate_entities(self):
        """Test deduping entire entities."""
        bbox = BoundingBox(min=Vector3(x=0, y=0, z=0), max=Vector3(x=1, y=1, z=0))
        e1 = Entity(
            id="e1", 
            type=EntityType.SOLID, 
            layer="0", 
            geometry={"x":0, "y":0, "z":0}, 
            bbox=bbox
        )
        # Duplicate of e1
        e2 = Entity(
            id="e2", 
            type=EntityType.SOLID, 
            layer="0", 
            geometry={"x":0.0001, "y":0, "z":0}, # Within tolerance
            bbox=bbox
        )
        # Different
        e3 = Entity(
            id="e3", 
            type=EntityType.SOLID, 
            layer="0", 
            geometry={"x":10, "y":10, "z":0}, 
            bbox=bbox
        )
        
        healed, actions = heal_topology([e1, e2, e3], tolerance=0.001)
        
        assert len(healed) == 2
        ids = {e.id for e in healed}
        assert "e1" in ids
        assert "e3" in ids
        assert "e2" not in ids
        
        assert len(actions) == 1
        assert actions[0].kind == HealingActionKind.DUPLICATE_REMOVE
        assert "e2" in actions[0].affected_entities

    def test_snap_to_grid(self):
        """Test grid snapping."""
        bbox = BoundingBox(min=Vector3(x=0, y=0, z=0), max=Vector3(x=1, y=1, z=0))
        e1 = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="0",
            geometry={
                "vertices": [
                    {"x": 0.0023, "y": 0.0051, "z": 0}, 
                ],
                "closed": False
            },
            bbox=bbox
        )
        
        # Grid 0.001 -> 0.002, 0.005
        healed, actions = heal_topology(
            [e1], 
            tolerance=0.0001, 
            snap_to_grid=True, 
            grid_size=0.001
        )
        
        v = healed[0].geometry["vertices"][0]
        assert v["x"] == 0.002
        assert v["y"] == 0.005
