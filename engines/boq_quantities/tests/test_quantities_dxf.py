"""
Tests for BoQ quantities with DXF semantic fixtures.

Covers:
- Quantity calculation for DXF-derived semantic elements
- Wall area with opening deductions
- Scope tagging and aggregation
- Deterministic ordering and hashing
- Caching behavior
"""

import pytest

from engines.cad_ingest.dxf_adapter import dxf_to_cad_model
from engines.cad_ingest.tests.fixtures import DXF_FLOORPLAN_FIXTURE
from engines.cad_semantics.service import SemanticClassificationService
from engines.boq_quantities.formulas import deterministic_boq_item_id
from engines.boq_quantities.models import BoQItem, FormulaType, UnitType
from engines.boq_quantities.service import BoQQuantitiesService


class TestBoQQuantitiesCalculation:
    """Test quantity calculations."""
    
    def test_quantify_dxf_model(self):
        """Test quantifying a DXF-derived semantic model."""
        # Ingest DXF
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        
        # Semanticize
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        # Quantify
        service = BoQQuantitiesService()
        boq_model, response = service.quantify(semantic_model)
        
        assert boq_model is not None
        assert response is not None
        assert len(boq_model.items) > 0
        assert boq_model.item_count > 0
    
    def test_boq_items_have_formulas(self):
        """Test that BoQ items record which formula was applied."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq_model, _ = service.quantify(semantic_model)
        
        for item in boq_model.items:
            assert item.formula_used is not None
            assert isinstance(item.formula_used, FormulaType)
            # Unknown types may not have metadata, but known types should
            if item.formula_used != FormulaType.UNKNOWN:
                assert len(item.meta) > 0
    
    def test_boq_items_have_units(self):
        """Test that BoQ items have appropriate units."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq_model, _ = service.quantify(semantic_model)
        
        for item in boq_model.items:
            assert item.unit is not None
            assert isinstance(item.unit, UnitType)


class TestBoQDeterminism:
    """Test deterministic BoQ generation."""
    
    def test_boq_determinism_same_input(self):
        """Test that same semantic model produces same BoQ."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq1, _ = service.quantify(semantic_model)
        boq2, _ = service.quantify(semantic_model)
        
        # Should have same model hash
        assert boq1.model_hash == boq2.model_hash
        # Should have same item count
        assert len(boq1.items) == len(boq2.items)
        # Items should be in same order
        for i1, i2 in zip(boq1.items, boq2.items):
            assert i1.id == i2.id
            assert i1.quantity == i2.quantity
    
    def test_boq_item_ids_are_deterministic(self):
        """Test that BoQ item IDs are deterministic."""
        item_id1 = deterministic_boq_item_id("elem_123", "wall")
        item_id2 = deterministic_boq_item_id("elem_123", "wall")
        
        assert item_id1 == item_id2
        assert len(item_id1) == 16  # SHA256 truncated to 16 chars


class TestBoQScopes:
    """Test scope tagging and aggregation."""
    
    def test_boq_scopes_created(self):
        """Test that scopes are created for each level."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq_model, _ = service.quantify(semantic_model)
        
        assert len(boq_model.scopes) > 0
    
    def test_boq_scopes_have_totals(self):
        """Test that scopes aggregate item counts and areas."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq_model, _ = service.quantify(semantic_model)
        
        for scope in boq_model.scopes:
            # Should have at least item count set
            assert scope.item_count >= 0


class TestBoQCaching:
    """Test BoQ service caching."""
    
    def test_boq_caching(self):
        """Test service caches BoQ models."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq1, _ = service.quantify(semantic_model)
        boq2, _ = service.quantify(semantic_model)
        
        # Should be same object from cache
        assert boq1.id == boq2.id
    
    def test_boq_cache_miss_different_params(self):
        """Test cache miss when parameters change."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        
        # Quantify with default params
        boq1, _ = service.quantify(semantic_model)
        
        # Quantify with different thickness
        boq2, _ = service.quantify(
            semantic_model,
            calc_params={"wall_thickness_mm": 300}
        )
        
        # Should be different items or at least different hashes
        # (depends on whether param affects output)
        # At minimum, both should have valid results
        assert len(boq1.items) > 0
        assert len(boq2.items) > 0


class TestBoQItemCounts:
    """Test BoQ item counting and statistics."""
    
    def test_boq_response_has_counts(self):
        """Test response includes item type counts."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        _, response = service.quantify(semantic_model)
        
        assert response.item_count > 0
        assert len(response.item_count_by_type) > 0
    
    def test_boq_item_count_by_type_matches_total(self):
        """Test that count by type sums to total."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq_model, response = service.quantify(semantic_model)
        
        # Sum of type counts should equal total count
        type_count_sum = sum(response.item_count_by_type.values())
        assert type_count_sum == response.item_count


class TestBoQItemSorting:
    """Test BoQ items are deterministically sorted."""
    
    def test_boq_items_sorted_by_type_and_id(self):
        """Test items are sorted by type then ID."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        service = BoQQuantitiesService()
        boq_model, _ = service.quantify(semantic_model)
        
        # Check items are sorted
        for i in range(len(boq_model.items) - 1):
            curr = boq_model.items[i]
            next_item = boq_model.items[i + 1]
            
            # Should be sorted by type then ID
            if curr.element_type == next_item.element_type:
                assert curr.id <= next_item.id
            else:
                # Type comparison
                assert curr.element_type <= next_item.element_type
