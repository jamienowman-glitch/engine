"""
Integration test for semantic artifact registration.
"""

import pytest
from engines.cad_ingest.models import CadModel, UnitKind, BoundingBox, Vector3, Entity, EntityType
from engines.cad_semantics.service import SemanticClassificationService
from engines.cad_semantics.models import SemanticType, SemanticModel, SpatialGraph

def create_mock_semantic_model() -> SemanticModel:
    model = SemanticModel(
        cad_model_id="cad1",
        rule_version="1.0.0",
        model_hash="abc1234_model",
    )
    model.spatial_graph = SpatialGraph(graph_hash="xyz789_graph")
    model.level_count = 5
    # Add dummy elements to have element_count
    for i in range(10):
        model.elements.append(
            # Just dummy object
            type("MockElem", (), {}) 
        )
    return model

class TestServiceRegistration:
    
    def test_register_artifact_compliant(self):
        """Verify register_artifact produces valid metadata matching schema."""
        service = SemanticClassificationService()
        
        # We need a proper SemanticModel structure
        e1 = Entity(
            id="e1", type=EntityType.LINE, layer="L", geometry={}, 
            bbox=BoundingBox(min=Vector3(x=0,y=0), max=Vector3(x=1,y=1))
        )
        cad_model = CadModel(
            source_uri="t", entities=[e1], source_format="dxf", source_sha256="s", model_hash="m",
            units=UnitKind.MILLIMETER, bbox=BoundingBox(min=Vector3(x=0,y=0), max=Vector3(x=10,y=10))
        )
        
        sem_model, _ = service.semanticize(cad_model)
        
        # Now register it
        artifact_id = service.register_artifact(cad_model.id, sem_model)
        
        assert artifact_id.startswith("sem_")
        assert sem_model.model_hash in artifact_id

    def test_register_artifact_validation_failure(self):
        """Verify that if we broke the service logic (missing fields), it would raise."""
        service = SemanticClassificationService()
        
        broken_model = SemanticModel(cad_model_id="c1")
        broken_model.spatial_graph = SpatialGraph(graph_hash="g")
        broken_model.model_hash = None # Triggers failure now that we check for None

        with pytest.raises(ValueError, match="cad_semantics requires meta fields"):
            service.register_artifact("c1", broken_model)
        # Force missing item by clearing it before check? 
        # Wait, the meta dict is constructed from the model fields. 
        # If I want to test that MISSING fields raise error, I need to ensure `register_artifact` 
        # So I'm testing `register_artifact`'s implementation?
        # Yes, but `register_artifact` is supposed to fill them.
        # If `SemanticModel` fields are Optionals that default to None, 
        # and `register_artifact` puts them in dict, then `DerivedArtifact` validation sees None?
        # Let's see models.py: model_hash is Optional[str] = None.
        # If I leave it None, meta['model_hash'] is None.
        # Strict validation `required_keys` checks `k not in meta`. 
        # If key IS in meta but value is None, what happens?
        # My validation logic: `missing = [k for k in required_keys if k not in meta]`
        # Use `k not in meta or meta[k] is None`?
        
        # Actually `DerivedArtifact` validation in `models.py` only checks `k not in meta`.
        # If key is present but None, it passes "presence" check.
        # I should probably update `models.py` to check for None or empty string too if I want STRICT.
        # But for now, let's see why it failed. 
        # `register_artifact` constructs `meta = {"model_hash": model.model_hash, ...}`.
        # So key "model_hash" IS in meta, value is None. 
        # So validator passes.
        
        # Correct fix: Update models.py to ensure value is truthy? 
        # Or change test to verifying that valid inputs pass. 
        # The goal is strict validation. I should enforce not-None.
        pass
