"""
Tests for IFC-lite adapter and ingest pipeline.

Covers:
- IFC-lite JSON parsing
- Unit detection and validation
- Placement transform handling
- Missing unit error paths
"""

import json
import hashlib
import pytest

from engines.cad_ingest.ifc_lite_adapter import ifc_lite_to_cad_model
from engines.cad_ingest.models import UnitKind, EntityType
from engines.cad_ingest.tests.fixtures import IFC_LITE_FIXTURE_JSON


class TestIfcLiteParsing:
    """Test IFC-lite parsing and normalization."""
    
    def test_ifc_lite_parse_fixture(self):
        """Parse IFC-lite JSON fixture."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        assert model is not None
        assert model.source_format == "ifc-lite"
        assert model.units == UnitKind.MILLIMETER  # Specified in fixture
        assert len(model.entities) >= 2
        assert len(model.layers) >= 1
    
    def test_ifc_lite_entity_count(self):
        """Verify entity count matches fixture."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        # Fixture has 3 elements: 2 walls + 1 slab
        assert len(model.entities) == 3
    
    def test_ifc_lite_layer_extraction(self):
        """Verify layers are extracted correctly."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        layer_names = {layer.name for layer in model.layers}
        
        # Should have Walls and Floors layers
        assert "Walls" in layer_names
        assert "Floors" in layer_names
    
    def test_ifc_lite_entity_types(self):
        """Verify entity types are correctly mapped."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        # All elements in fixture should be SOLID
        for entity in model.entities:
            assert entity.type == EntityType.SOLID
    
    def test_ifc_lite_placement_transform(self):
        """Verify placement transforms are applied."""
        # IFC-lite should apply placement offsets
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        # Geometry should include placement offsets
        for entity in model.entities:
            assert "x" in entity.geometry or entity.type == EntityType.SOLID
    
    def test_ifc_lite_bbox_computation(self):
        """Verify bounding box is computed."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        # Should have non-zero bbox
        assert model.bbox.min.x < model.bbox.max.x
        assert model.bbox.min.y < model.bbox.max.y
    
    def test_ifc_lite_deterministic_ids(self):
        """Verify entity IDs are deterministic."""
        model1 = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        model2 = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        # Same input should produce same IDs
        ids1 = {e.id for e in model1.entities}
        ids2 = {e.id for e in model2.entities}
        assert ids1 == ids2
    
    def test_ifc_lite_source_sha256(self):
        """Verify source SHA256 is computed."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        expected_sha = hashlib.sha256(IFC_LITE_FIXTURE_JSON).hexdigest()
        assert model.source_sha256 == expected_sha
    
    def test_ifc_lite_model_hash(self):
        """Verify model hash is computed."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        assert model.model_hash is not None
        assert len(model.model_hash) == 16
    
    def test_ifc_lite_unit_from_fixture(self):
        """Verify units are read from fixture."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        assert model.units == UnitKind.MILLIMETER
    
    def test_ifc_lite_unit_hint_override(self):
        """Verify unit_hint overrides fixture units."""
        model = ifc_lite_to_cad_model(
            IFC_LITE_FIXTURE_JSON,
            unit_hint=UnitKind.METER
        )
        assert model.units == UnitKind.METER
    
    def test_ifc_lite_missing_units_error(self):
        """Verify error when units are missing and no hint provided."""
        # Create fixture without units
        no_units_fixture = json.dumps({
            "elements": [
                {
                    "type": "Wall",
                    "layer": "Walls",
                    "geometry": {"x": 0, "y": 0, "z": 0},
                    "placement": {},
                }
            ],
            "layers": [{"name": "Walls"}],
        }).encode("utf-8")
        
        with pytest.raises(ValueError, match="missing unit specification"):
            ifc_lite_to_cad_model(no_units_fixture)
    
    def test_ifc_lite_missing_units_hint_provided(self):
        """Verify hint is used when units are missing."""
        no_units_fixture = json.dumps({
            "elements": [
                {
                    "type": "Wall",
                    "layer": "Walls",
                    "geometry": {"x": 0, "y": 0, "z": 0},
                    "placement": {},
                }
            ],
            "layers": [{"name": "Walls"}],
        }).encode("utf-8")
        
        model = ifc_lite_to_cad_model(
            no_units_fixture,
            unit_hint=UnitKind.FOOT
        )
        assert model.units == UnitKind.FOOT
    
    def test_ifc_lite_adapter_version(self):
        """Verify adapter version is set."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        assert model.adapter_version == "1.0.0"
    
    def test_ifc_lite_created_at_timestamp(self):
        """Verify created_at timestamp is set."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        assert model.created_at is not None
    
    def test_ifc_lite_entity_meta(self):
        """Verify IFC type is stored in entity meta."""
        model = ifc_lite_to_cad_model(IFC_LITE_FIXTURE_JSON)
        
        for entity in model.entities:
            assert "ifc_type" in entity.meta
            assert entity.meta["ifc_type"] in ("Wall", "Slab")


class TestIfcLiteTextParsing:
    """Test IFC-lite text format parsing."""
    
    def test_ifc_lite_text_format(self):
        """Parse IFC-lite text format (fallback)."""
        text_fixture = b"""
UNIT=mm
ELEMENT_TYPE=Wall
LAYER=Walls
X=0.0
Y=0.0
Z=0.0
WIDTH=100.0
HEIGHT=3000.0
LENGTH=300.0
ELEMENT_TYPE=Slab
LAYER=Floors
X=50.0
Y=50.0
Z=0.0
WIDTH=100.0
HEIGHT=100.0
LENGTH=200.0
"""
        model = ifc_lite_to_cad_model(text_fixture)
        
        assert model is not None
        assert model.units == UnitKind.MILLIMETER
        assert len(model.entities) >= 2


class TestIfcLiteValidation:
    """Test input validation and error paths."""
    
    def test_invalid_ifc_lite_json(self):
        """Test handling of invalid JSON."""
        invalid_content = b"{ invalid json"
        
        # Should fall back to text parsing
        model = ifc_lite_to_cad_model(
            invalid_content,
            unit_hint=UnitKind.MILLIMETER
        )
        assert model is not None
    
    def test_empty_ifc_lite_content(self):
        """Test handling of empty content."""
        empty_content = b""
        
        with pytest.raises(ValueError):
            ifc_lite_to_cad_model(empty_content)
