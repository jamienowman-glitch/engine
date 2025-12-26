"""
Tests for CAD level detection and metadata.
"""

import pytest
from engines.cad_ingest.models import Entity, EntityType, BoundingBox, Vector3, CadModel, UnitKind
from engines.cad_semantics.service import SemanticClassificationService
from engines.cad_semantics.rules import infer_levels_from_elevations

def create_entity_z(id: str, z: float) -> Entity:
    return Entity(
        id=id,
        type=EntityType.LINE,
        layer="L",
        geometry={},
        bbox=BoundingBox(min=Vector3(x=0,y=0,z=z), max=Vector3(x=10,y=10,z=z))
    )

def create_entity_no_z(id: str) -> Entity:
    # bbox with None z? Or just use default 0? 
    # Current codebase might default to 0.0 in some places, 
    # but let's see how `infer_levels_from_elevations` detects usage.
    # It checks `entity.bbox.min.z`.
    # Pydantic model for Vector3 usually requires z, defaults to 0.0?
    # Let's assume we can simulate "no elevation" by maybe having 2D vectors in a 3D struct 
    # or just pass a None if allowed. 
    # Looking at `engines/cad_ingest/models.py`, Vector3 has `z: float = 0.0`.
    # So "no elevation" data implies everything is at 0.0.
    # However, `dxf_adapter` sets z from geometry.
    # The rule says: `if z is not None: elevations.append(z)`.
    # If Vector3.z defaults to 0.0, then it's always not None.
    # Wait, `rules.py` said `if z is not None`.
    # Let's check if z can be None in Vector3.
    # If it is strict float, it can't be None.
    # If 2D processing sets it to 0, then we have 1 level at 0.0.
    # The warning "No entity elevations found" might be for when `entities` list is empty 
    # OR if we explicitly allow Z to be None. 
    # The implementation I wrote checks `if z is not None`.
    # I will stick to what the code does. 
    pass

class TestLevelDetection:
    
    def test_infer_levels_warning_on_empty(self):
        """Test warning when no elevations available (empty entities)."""
        levels, warning = infer_levels_from_elevations([])
        assert "L0" in levels.values()
        assert warning is not None
        assert "defaulting to L0" in warning

    def test_infer_levels_valid_3d(self):
        """Test inference on valid 3D entities."""
        e1 = create_entity_z("e1", 0.0)
        e2 = create_entity_z("e2", 3.5)
        
        levels, warning = infer_levels_from_elevations([e1, e2])
        assert warning is None
        assert len(levels) == 2
        assert levels[0.0] != levels[3.5]

    def test_service_propagates_meta(self):
        """Test that service puts level summary and warnings in meta."""
        service = SemanticClassificationService()
        
        # Scenario 1: No warning
        e1 = create_entity_z("e1", 0.0)
        model = CadModel(
            source_uri="t", entities=[e1], source_format="dxf", source_sha256="a", model_hash="m",
            units=UnitKind.MILLIMETER,
            bbox=BoundingBox(min=Vector3(x=0,y=0), max=Vector3(x=10,y=10))
        )
        sem_model, response = service.semanticize(model)
        
        assert not sem_model.warnings
        assert "level_summary" in response.meta
        assert response.meta["level_summary"]["L0"] == 0.0
        assert not response.meta["warnings"]

        # Scenario 2: Warning (empty entities?)
        # A model with no entities is weird, but technically possible via API maybe?
        # Let's force empty entities to trigger the warning logic
        model_empty = CadModel(
            source_uri="t", entities=[], source_format="dxf", source_sha256="b", model_hash="m2",
            units=UnitKind.MILLIMETER,
            bbox=BoundingBox(min=Vector3(x=0,y=0), max=Vector3(x=10,y=10))
        )
        sem_model_w, response_w = service.semanticize(model_empty)
        
        assert len(sem_model_w.warnings) > 0
        assert "defaulting to L0" in sem_model_w.warnings[0]
        assert "warnings" in response_w.meta
        assert len(response_w.meta["warnings"]) > 0
