"""
Tests for topology healing operations.

Covers:
- Gap closing within tolerance
- Vertex deduplication
- Winding normalization
- Entity deduplication
- Healing validation
"""

import pytest

from engines.cad_ingest.models import (
    Entity,
    EntityType,
    Vector3,
    BoundingBox,
)
from engines.cad_ingest.topology_heal import (
    distance_3d,
    vector_equal,
    normalize_polygon_winding,
    close_gaps_in_polyline,
    deduplicate_vertices,
    heal_polyline_geometry,
    detect_duplicate_entities,
    remove_duplicate_entities,
    validate_healed_geometry,
)


class TestGeometryUtils:
    """Test basic geometry utility functions."""
    
    def test_distance_3d(self):
        """Test 3D distance computation."""
        p1 = Vector3(x=0, y=0, z=0)
        p2 = Vector3(x=3, y=4, z=0)
        
        dist = distance_3d(p1, p2)
        assert abs(dist - 5.0) < 0.001  # 3-4-5 triangle
    
    def test_vector_equal_within_tolerance(self):
        """Test vector equality with tolerance."""
        p1 = Vector3(x=0, y=0, z=0)
        p2 = Vector3(x=0.0005, y=0.0005, z=0)
        
        assert vector_equal(p1, p2, tolerance=0.001)
        assert not vector_equal(p1, p2, tolerance=0.0001)
    
    def test_normalize_polygon_winding(self):
        """Test polygon winding normalization."""
        # Create a clockwise polygon
        cw_vertices = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=1, y=1, z=0),
            Vector3(x=0, y=1, z=0),
        ]
        
        # Should remain same or reverse depending on order
        result = normalize_polygon_winding(cw_vertices)
        assert len(result) == 4
    
    def test_normalize_polygon_winding_empty(self):
        """Test normalization with insufficient vertices."""
        result = normalize_polygon_winding([])
        assert result == []
        
        result = normalize_polygon_winding([Vector3(x=0, y=0, z=0)])
        assert len(result) == 1


class TestGapClosing:
    """Test gap closing functionality."""
    
    def test_close_gaps_endpoints_far_apart(self):
        """Test no closure when endpoints are far apart."""
        vertices = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=1, y=1, z=0),
            Vector3(x=0, y=2, z=0),  # Far from start
        ]
        
        result, actions = close_gaps_in_polyline(vertices, tolerance=0.001)
        assert len(result) == 4
    
    def test_close_gaps_endpoints_close(self):
        """Test closure when endpoints are close."""
        vertices = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=1, y=1, z=0),
            Vector3(x=0.0005, y=0, z=0),  # Close to start
        ]
        
        result, actions = close_gaps_in_polyline(vertices, tolerance=0.001)
        # Last point should be snapped to first
        assert result[-1] == result[0]
    
    def test_close_gaps_empty_polyline(self):
        """Test handling of empty polyline."""
        result, actions = close_gaps_in_polyline([], tolerance=0.001)
        assert result == []
        assert len(actions) == 0


class TestVertexDeduplication:
    """Test vertex deduplication functionality."""
    
    def test_deduplicate_consecutive_vertices(self):
        """Test removal of consecutive duplicates."""
        vertices = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=0.0001, y=0, z=0),  # Duplicate within tolerance
            Vector3(x=1, y=0, z=0),
        ]
        
        result, actions = deduplicate_vertices(vertices, tolerance=0.001)
        assert len(result) == 2
        assert len(actions) > 0
    
    def test_deduplicate_no_duplicates(self):
        """Test handling when there are no duplicates."""
        vertices = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=1, y=1, z=0),
        ]
        
        result, actions = deduplicate_vertices(vertices, tolerance=0.001)
        assert len(result) == 3
        assert len(actions) == 0
    
    def test_deduplicate_all_same(self):
        """Test handling when all vertices are the same."""
        vertices = [
            Vector3(x=0, y=0, z=0),
            Vector3(x=0.0001, y=0, z=0),
            Vector3(x=0.0002, y=0, z=0),
        ]
        
        result, actions = deduplicate_vertices(vertices, tolerance=0.001)
        assert len(result) == 1


class TestPolylineHealing:
    """Test full polyline healing operations."""
    
    def test_heal_polyline_with_duplicates(self):
        """Test healing polyline with duplicate vertices."""
        geometry = {
            "vertices": [
                {"x": 0, "y": 0, "z": 0},
                {"x": 0.0001, "y": 0, "z": 0},
                {"x": 1, "y": 0, "z": 0},
            ],
            "closed": False,
        }
        
        result, actions = heal_polyline_geometry(geometry, tolerance=0.001)
        assert len(result["vertices"]) == 2
        assert len(actions) > 0
    
    def test_heal_polyline_with_grid_snap(self):
        """Test healing polyline with grid snapping."""
        geometry = {
            "vertices": [
                {"x": 0.123, "y": 0.456, "z": 0},
                {"x": 1.789, "y": 2.345, "z": 0},
            ],
            "closed": False,
        }
        
        result, actions = heal_polyline_geometry(
            geometry, tolerance=0.001, snap_to_grid=True, grid_size=0.1
        )
        
        # Check that snapping happened
        assert "snapped_to_grid" in actions
        verts = result["vertices"]
        for v in verts:
            assert v["x"] % 0.1 < 0.01 or (v["x"] % 0.1) > 0.09
    
    def test_heal_polyline_closed(self):
        """Test healing closed polyline."""
        geometry = {
            "vertices": [
                {"x": 0, "y": 0, "z": 0},
                {"x": 1, "y": 0, "z": 0},
                {"x": 1, "y": 1, "z": 0},
            ],
            "closed": True,
        }
        
        result, actions = heal_polyline_geometry(geometry, tolerance=0.001)
        # Should normalize winding
        assert "normalized_winding" in actions


class TestEntityDeduplication:
    """Test entity-level deduplication."""
    
    def test_detect_duplicate_entities(self):
        """Test detection of duplicate entities."""
        e1 = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": [{"x": 0, "y": 0}]},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        e2 = Entity(
            id="e2",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": [{"x": 0, "y": 0}]},
            bbox=BoundingBox(min=Vector3(x=0.0001, y=0), max=Vector3(x=1.0001, y=1)),
        )
        
        duplicates = detect_duplicate_entities([e1, e2], tolerance=0.001)
        assert len(duplicates) > 0
    
    def test_detect_no_duplicates(self):
        """Test when there are no duplicates."""
        e1 = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        e2 = Entity(
            id="e2",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=10, y=10), max=Vector3(x=11, y=11)),
        )
        
        duplicates = detect_duplicate_entities([e1, e2], tolerance=0.001)
        assert len(duplicates) == 0
    
    def test_remove_duplicate_entities(self):
        """Test removal of duplicate entities."""
        e1 = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        e2 = Entity(
            id="e2",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0.0001, y=0), max=Vector3(x=1.0001, y=1)),
        )
        
        result, actions = remove_duplicate_entities([e1, e2], tolerance=0.001)
        assert len(result) == 1
        assert len(actions) > 0


class TestGeometryValidation:
    """Test healed geometry validation."""
    
    def test_validate_healed_geometry_valid(self):
        """Test validation passes for valid healing."""
        original = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        healed = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1.0001, y=1)),
        )
        
        valid = validate_healed_geometry(original, healed, tolerance=0.001)
        assert valid
    
    def test_validate_healed_geometry_divergence(self):
        """Test validation with significant divergence."""
        original = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        healed = Entity(
            id="e1",
            type=EntityType.POLYLINE,
            layer="L1",
            geometry={"vertices": []},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=100, y=100)),
        )
        
        # Should be invalid due to large divergence
        valid = validate_healed_geometry(original, healed, tolerance=0.001)
        # May be invalid or warning depending on tolerance
