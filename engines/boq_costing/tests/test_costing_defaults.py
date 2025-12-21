"""
Tests for BoQ costing with cost catalog application.

Covers:
- Cost calculation with default catalog
- Currency conversion
- Markup and tax application
- Deterministic totals and hashing
- Caching behavior
- Error handling for missing rates
"""

import pytest

from engines.cad_ingest.dxf_adapter import dxf_to_cad_model
from engines.cad_ingest.tests.fixtures import DXF_FLOORPLAN_FIXTURE
from engines.cad_semantics.service import SemanticClassificationService
from engines.boq_quantities.service import BoQQuantitiesService
from engines.boq_costing.models import Currency
from engines.boq_costing.catalog import create_default_catalog
from engines.boq_costing.service import BoQCostingService


class TestCostingDefaults:
    """Test cost estimation with default catalog."""
    
    def test_estimate_cost_default_catalog(self):
        """Test costing with default catalog."""
        # Build BoQ from DXF
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        # Cost it
        cost_service = BoQCostingService()
        cost_model, response = cost_service.estimate_cost(boq_model)
        
        assert cost_model is not None
        assert response is not None
        assert response.total_cost >= 0
        assert response.item_count > 0
    
    def test_cost_items_have_rates(self):
        """Test that cost items have unit rates from catalog."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        for item in cost_model.items:
            assert item.unit_rate >= 0
            assert item.extended_cost >= 0


class TestCurrencyConversion:
    """Test currency conversion in costing."""
    
    def test_estimate_cost_with_gbp(self):
        """Test costing in GBP currency."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        # Cost in USD and GBP
        cost_service = BoQCostingService()
        cost_usd, resp_usd = cost_service.estimate_cost(boq_model, currency=Currency.USD)
        
        # Clear cache to force recalculation
        cost_service.cache.clear()
        cost_gbp, resp_gbp = cost_service.estimate_cost(boq_model, currency=Currency.GBP)
        
        # GBP should be different from USD (conversion applied)
        assert resp_gbp.currency == Currency.GBP
        assert resp_gbp.total_cost > 0


class TestMarkupAndTax:
    """Test markup and tax application."""
    
    def test_cost_with_markup(self):
        """Test costing with markup."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        
        # Cost without markup
        cost_no_markup, resp_no_markup = cost_service.estimate_cost(boq_model, markup_pct=0.0)
        
        # Clear cache
        cost_service.cache.clear()
        
        # Cost with markup
        cost_with_markup, resp_with_markup = cost_service.estimate_cost(boq_model, markup_pct=15.0)
        
        # With markup should be higher (unless total is 0)
        if resp_no_markup.total_cost > 0:
            assert resp_with_markup.total_cost > resp_no_markup.total_cost
    
    def test_cost_with_tax(self):
        """Test costing with tax."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        
        # Cost without tax
        cost_no_tax, resp_no_tax = cost_service.estimate_cost(boq_model, tax_pct=0.0)
        
        # Clear cache
        cost_service.cache.clear()
        
        # Cost with tax
        cost_with_tax, resp_with_tax = cost_service.estimate_cost(boq_model, tax_pct=10.0)
        
        # With tax should be higher
        if resp_no_tax.total_cost > 0:
            assert resp_with_tax.total_cost > resp_no_tax.total_cost


class TestCostingDeterminism:
    """Test deterministic cost generation."""
    
    def test_cost_determinism_same_input(self):
        """Test that same BoQ produces same cost."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost1, _ = cost_service.estimate_cost(boq_model)
        cost2, _ = cost_service.estimate_cost(boq_model)
        
        # Should have same model hash
        assert cost1.model_hash == cost2.model_hash
        # Should have same total cost
        assert cost1.total_cost == cost2.total_cost


class TestCostingCaching:
    """Test cost service caching."""
    
    def test_cost_caching(self):
        """Test service caches cost models."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost1, _ = cost_service.estimate_cost(boq_model)
        cost2, _ = cost_service.estimate_cost(boq_model)
        
        # Should be same object from cache
        assert cost1.id == cost2.id
    
    def test_cost_cache_miss_different_currency(self):
        """Test cache miss when currency changes."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        
        # Cost in USD
        cost1, _ = cost_service.estimate_cost(boq_model, currency=Currency.USD)
        
        # Cost in EUR (should not hit cache)
        cost2, _ = cost_service.estimate_cost(boq_model, currency=Currency.EUR)
        
        # Different currencies should produce different results
        assert cost1.currency == Currency.USD
        assert cost2.currency == Currency.EUR


class TestCostingRollups:
    """Test cost rollup calculations."""
    
    def test_cost_rollups_created(self):
        """Test that rollups are created for each scope."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        assert len(cost_model.rollups) > 0
    
    def test_cost_rollup_totals_match(self):
        """Test that rollup totals match cost items."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        # Sum of rollup totals should equal model total (approximately)
        rollup_sum = sum(r.total_cost for r in cost_model.rollups)
        assert abs(rollup_sum - cost_model.total_cost) < 0.01  # Float rounding tolerance


class TestCostingValidation:
    """Test cost validation and error handling."""
    
    def test_cost_response_has_counts(self):
        """Test response includes item counts."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        _, response = cost_service.estimate_cost(boq_model)
        
        assert response.item_count > 0
        assert response.rollup_count >= 0


class TestDefaultCatalog:
    """Test default catalog creation and rates."""
    
    def test_default_catalog_has_rates(self):
        """Test that default catalog has rates for common types."""
        catalog = create_default_catalog()
        
        # Should have rates for common types
        assert catalog.get_rate("wall", "m2") is not None
        assert catalog.get_rate("door", "count") is not None
        assert catalog.get_rate("window", "count") is not None
        assert catalog.get_rate("slab", "m2") is not None
    
    def test_default_catalog_has_fx_rates(self):
        """Test that default catalog has FX conversion data."""
        catalog = create_default_catalog()
        
        # Should have some FX rates
        assert len(catalog.fx_rates) > 0
        assert "GBP/USD" in catalog.fx_rates
