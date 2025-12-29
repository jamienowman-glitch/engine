"""
Tests for CAD semantic classification and spatial graph building.

Covers:
- Element classification by layer name and geometry
- Level detection from elevations
- Spatial graph construction
- Deterministic IDs and hashing
"""

import pytest

from engines.cad_ingest.dxf_adapter import dxf_to_cad_model
from engines.cad_ingest.ifc_lite_adapter import ifc_lite_to_cad_model
from engines.cad_ingest.models import EntityType, UnitKind
from engines.cad_ingest.tests.fixtures import DXF_FLOORPLAN_FIXTURE, IFC_LITE_FIXTURE_JSON
from engines.cad_semantics.graph import build_spatial_graph
from engines.cad_semantics.models import SemanticType
from engines.cad_semantics.rules import ClassificationRuleSet, infer_levels_from_elevations
from engines.cad_semantics.service import SemanticClassificationService


class TestClassificationRules:
    """Test semantic classification rules."""
    
    def test_wall_rule_matching(self):
        """Test wall rule matches layer names."""
        ruleset = ClassificationRuleSet()
        
        # Create mock entity
        from engines.cad_ingest.models import Entity, BoundingBox, Vector3
        
        entity = Entity(
            id="wall1",
            type=EntityType.POLYLINE,
            layer="Wall",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        
        sem_type, hits, conf = ruleset.classify(entity, "Wall")
        assert sem_type == SemanticType.WALL
        assert len(hits) > 0
        assert conf > 0.5
    
    def test_door_rule_matching(self):
        """Test door rule matches layer names."""
        ruleset = ClassificationRuleSet()
        
        from engines.cad_ingest.models import Entity, BoundingBox, Vector3
        
        entity = Entity(
            id="door1",
            type=EntityType.CIRCLE,
            layer="Door",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        
        sem_type, hits, conf = ruleset.classify(entity, "Door")
        assert sem_type == SemanticType.DOOR
    
    def test_window_rule_matching(self):
        """Test window rule matches."""
        ruleset = ClassificationRuleSet()
        
        from engines.cad_ingest.models import Entity, BoundingBox, Vector3
        
        entity = Entity(
            id="window1",
            type=EntityType.CIRCLE,
            layer="Window",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        
        sem_type, hits, conf = ruleset.classify(entity, "Window")
        assert sem_type == SemanticType.WINDOW
    
    def test_unknown_classification(self):
        """Test unknown classification."""
        ruleset = ClassificationRuleSet()
        
        from engines.cad_ingest.models import Entity, BoundingBox, Vector3
        
        entity = Entity(
            id="unknown1",
            type=EntityType.LINE,
            layer="Random",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0), max=Vector3(x=1, y=1)),
        )
        
        sem_type, hits, conf = ruleset.classify(entity, "Random")
        assert sem_type == SemanticType.UNKNOWN
        assert conf == 0.0


class TestLevelInference:
    """Test building level detection."""
    
    def test_infer_levels_single_elevation(self):
        """Test level inference with single elevation."""
        from engines.cad_ingest.models import Entity, BoundingBox, Vector3
        
        entity = Entity(
            id="e1",
            type=EntityType.LINE,
            layer="L0",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0, z=0), max=Vector3(x=1, y=1, z=0)),
        )
        
        levels, _ = infer_levels_from_elevations([entity])
        assert 0.0 in levels
        assert levels[0.0] == "L0"
    
    def test_infer_levels_multiple_elevations(self):
        """Test level inference with multiple elevations."""
        from engines.cad_ingest.models import Entity, BoundingBox, Vector3
        
        entity1 = Entity(
            id="e1",
            type=EntityType.LINE,
            layer="L0",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0, z=0), max=Vector3(x=1, y=1, z=0)),
        )
        entity2 = Entity(
            id="e2",
            type=EntityType.LINE,
            layer="L1",
            geometry={},
            bbox=BoundingBox(min=Vector3(x=0, y=0, z=3), max=Vector3(x=1, y=1, z=3)),
        )
        
        levels, _ = infer_levels_from_elevations([entity1, entity2])
        assert 0.0 in levels
        assert 3.0 in levels
        assert levels[0.0] != levels[3.0]


class TestSpatialGraph:
    """Test spatial graph construction."""
    
    def test_graph_node_creation(self):
        """Test graph creates nodes for all elements."""
        from engines.cad_semantics.models import SemanticElement, SemanticType
        
        elem1 = SemanticElement(
            id="elem1",
            cad_entity_id="e1",
            semantic_type=SemanticType.WALL,
            layer="Wall",
            geometry_ref={"x": 0, "y": 0},
        )
        elem2 = SemanticElement(
            id="elem2",
            cad_entity_id="e2",
            semantic_type=SemanticType.DOOR,
            layer="Door",
            geometry_ref={"x": 1, "y": 0},
        )
        
        graph = build_spatial_graph([elem1, elem2])
        
        assert len(graph.nodes) == 2
        node_ids = {n.node_id for n in graph.nodes}
        assert elem1.id in node_ids
        assert elem2.id in node_ids
    
    def test_graph_adjacency_detection(self):
        """Test adjacency edge detection."""
        from engines.cad_semantics.models import SemanticElement, SemanticType
        
        # Create two adjacent elements
        elem1 = SemanticElement(
            id="elem1",
            cad_entity_id="e1",
            semantic_type=SemanticType.WALL,
            layer="Wall",
            geometry_ref={"x": 0, "y": 0},
        )
        elem2 = SemanticElement(
            id="elem2",
            cad_entity_id="e2",
            semantic_type=SemanticType.WALL,
            layer="Wall",
            geometry_ref={"x": 0.05, "y": 0},  # Close to elem1
        )
        
        graph = build_spatial_graph([elem1, elem2])
        
        # Should have at least one adjacency edge
        adjacency_edges = [e for e in graph.edges if e.edge_type.value == "adjacent"]
        assert len(adjacency_edges) > 0
    
    def test_graph_determinism(self):
        """Test graph hashing is deterministic."""
        from engines.cad_semantics.models import SemanticElement, SemanticType
        
        elem = SemanticElement(
            id="elem1",
            cad_entity_id="e1",
            semantic_type=SemanticType.WALL,
            layer="Wall",
            geometry_ref={"x": 0, "y": 0},
        )
        
        graph1 = build_spatial_graph([elem])
        graph2 = build_spatial_graph([elem])
        
        assert graph1.graph_hash == graph2.graph_hash


class TestSemanticService:
    """Test semantic classification service."""
    
    def test_semanticize_dxf_model(self):
        """Test semanticizing a DXF model."""
        service = SemanticClassificationService()
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        semantic_model, response = service.semanticize(cad_model)
        
        assert semantic_model is not None
        assert response is not None
        assert len(semantic_model.elements) > 0
        assert semantic_model.level_count >= 1
    
    def test_semanticize_ifc_lite_model(self):
        """Test semanticizing an IFC-lite model."""
        service = SemanticClassificationService()
        cad_model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        semantic_model, response = service.semanticize(cad_model)
        
        assert semantic_model is not None
        assert response is not None
        assert response.element_count > 0
    
    def test_semantics_determinism(self):
        """Test that same CAD model produces same semantics."""
        service = SemanticClassificationService()
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        sem1, _ = service.semanticize(cad_model)
        sem2, _ = service.semanticize(cad_model)
        
        # Should have same model hash
        assert sem1.model_hash == sem2.model_hash
        # Should have same element count
        assert len(sem1.elements) == len(sem2.elements)
    
    def test_semantics_caching(self):
        """Test service caching."""
        service = SemanticClassificationService()
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        sem1, _ = service.semanticize(cad_model)
        sem2, _ = service.semanticize(cad_model)
        
        # Should be same object (from cache)
        assert sem1.id == sem2.id
    
    def test_element_counts_in_response(self):
        """Test response includes element counts."""
        service = SemanticClassificationService()
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        _, response = service.semanticize(cad_model)
        
        # Should have some counts
        assert response.element_count >= 0
        assert response.wall_count >= 0
        assert response.door_count >= 0
        assert response.window_count >= 0
    
    def test_spatial_graph_in_semantic_model(self):
        """Test semantic model includes spatial graph."""
        service = SemanticClassificationService()
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        semantic_model, _ = service.semanticize(cad_model)
        
        assert semantic_model.spatial_graph is not None
        assert len(semantic_model.spatial_graph.nodes) > 0
        assert semantic_model.spatial_graph.graph_hash is not None
