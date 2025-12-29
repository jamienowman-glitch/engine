"""
Tests for DXF adapter and ingest pipeline.

Covers:
- DXF parsing and entity extraction
- Units conversion and detection
- Deterministic ID generation
- Caching
"""

import hashlib
import pytest

from engines.cad_ingest.dxf_adapter import dxf_to_cad_model
from engines.cad_ingest.models import UnitKind, EntityType
from engines.cad_ingest.tests.fixtures import DXF_FLOORPLAN_FIXTURE


class TestDxfParsing:
    """Test DXF parsing and normalization."""
    
    def test_dxf_parse_floorplan(self):
        """Parse DXF floorplan fixture."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        assert model is not None
        assert model.source_format == "dxf"
        assert model.units == UnitKind.MILLIMETER  # Explicit in fixture (code 4)
        assert len(model.entities) > 0
        assert len(model.layers) >= 1
    
    def test_dxf_strict_units_missing(self):
        """Verify ValueError when units are missing and no hint provided."""
        # DXF header without $UNITS
        no_units_dxf = b"""0
SECTION
2
HEADER
0
ENDSEC
0
EOF
"""
        with pytest.raises(ValueError, match="missing unit specification"):
            dxf_to_cad_model(no_units_dxf)

    def test_dxf_strict_units_missing_with_hint(self):
        """Verify success when units are missing but hint IS provided."""
        no_units_dxf = b"""0
SECTION
2
HEADER
0
ENDSEC
0
EOF
"""
        model = dxf_to_cad_model(no_units_dxf, unit_hint=UnitKind.METER)
        assert model.units == UnitKind.METER

    def test_dxf_entity_count(self):
        """Verify entity count matches fixture."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        # DXF_FLOORPLAN has 6 entities (4 lines + 2 circles)
        assert len(model.entities) == 6
    
    def test_dxf_layer_extraction(self):
        """Verify layers are extracted correctly."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        layer_names = {layer.name for layer in model.layers}
        
        # Should have Wall, Door, Window layers
        assert "Wall" in layer_names
        assert "Door" in layer_names
        assert "Window" in layer_names
    
    def test_dxf_bbox_computation(self):
        """Verify bounding box is computed correctly."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        # Fixture has bounds roughly 0-100 in x, 0-100 in y
        assert model.bbox.min.x <= 0.0
        assert model.bbox.max.x >= 100.0
        assert model.bbox.min.y <= 0.0
        assert model.bbox.max.y >= 100.0
    
    def test_dxf_deterministic_ids(self):
        """Verify entity IDs are deterministic."""
        model1 = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        model2 = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        # Same input should produce same IDs
        ids1 = {e.id for e in model1.entities}
        ids2 = {e.id for e in model2.entities}
        assert ids1 == ids2
    
    def test_dxf_source_sha256(self):
        """Verify source SHA256 is computed."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        expected_sha = hashlib.sha256(DXF_FLOORPLAN_FIXTURE).hexdigest()
        assert model.source_sha256 == expected_sha
    
    def test_dxf_model_hash(self):
        """Verify model hash is computed."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        assert model.model_hash is not None
        assert len(model.model_hash) == 16  # SHA256 hex[:16]
    
    def test_dxf_unit_hint_override(self):
        """Verify unit_hint overrides detected units."""
        model = dxf_to_cad_model(
            DXF_FLOORPLAN_FIXTURE,
            unit_hint=UnitKind.FOOT
        )
        assert model.units == UnitKind.FOOT
    
    def test_dxf_tolerance_parameter(self):
        """Verify tolerance parameter is set."""
        model = dxf_to_cad_model(
            DXF_FLOORPLAN_FIXTURE,
            tolerance=0.01
        )
        assert model.tolerance == 0.01
    
    def test_dxf_entity_types(self):
        """Verify entity types are correctly mapped."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        # Should have some LINE entities
        line_entities = [e for e in model.entities if e.type == EntityType.LINE]
        assert len(line_entities) >= 4
        
        # Should have some CIRCLE entities
        circle_entities = [e for e in model.entities if e.type == EntityType.CIRCLE]
        assert len(circle_entities) >= 2
    
    def test_dxf_entity_layer_assignment(self):
        """Verify entities are assigned to correct layers."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        # Wall entities should have layer "Wall"
        wall_entities = [e for e in model.entities if e.layer == "Wall"]
        assert len(wall_entities) > 0
    
    def test_dxf_adapter_version(self):
        """Verify adapter version is set."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        assert model.adapter_version == "1.0.0"
    
    def test_dxf_created_at_timestamp(self):
        """Verify created_at timestamp is set."""
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        assert model.created_at is not None


class TestDxfCaching:
    """Test ingest caching by source SHA256 + params."""
    
    def test_cache_hit_same_content(self):
        """Test that identical content is cached."""
        from engines.cad_ingest.service import CadIngestCache
        
        cache = CadIngestCache()
        
        key1 = cache.cache_key("abc123", "params1")
        model1 = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        cache.put(key1, model1)
        
        retrieved = cache.get(key1)
        assert retrieved is not None
        assert retrieved.id == model1.id
    
    def test_cache_miss_different_params(self):
        """Test that different params result in different cache entries."""
        from engines.cad_ingest.service import CadIngestCache
        
        cache = CadIngestCache()
        
        key1 = cache.cache_key("abc123", "params1")
        key2 = cache.cache_key("abc123", "params2")
        
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        cache.put(key1, model)
        
        retrieved = cache.get(key2)
        assert retrieved is None
    
    def test_cache_eviction(self):
        """Test simple FIFO eviction when cache is full."""
        from engines.cad_ingest.service import CadIngestCache
        
        cache = CadIngestCache(max_entries=2)
        
        model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        cache.put("key1", model)
        cache.put("key2", model)
        cache.put("key3", model)  # Should evict key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None


class TestDxfValidation:
    """Test input validation and error paths."""
    
    def test_invalid_dxf_content(self):
        """Test handling of malformed DXF."""
        invalid_content = b"not a valid dxf file"
        
        # Must provide unit hint for invalid files that lack headers
        model = dxf_to_cad_model(
            invalid_content,
            unit_hint=UnitKind.MILLIMETER
        )
        assert model is not None
        assert model.source_format == "dxf"
    
    def test_empty_dxf_content(self):
        """Test handling of empty DXF."""
        empty_content = b""
        
        # Empty file lacks units, so it must raise ValueError
        with pytest.raises(ValueError, match="missing unit specification"):
            dxf_to_cad_model(empty_content)
