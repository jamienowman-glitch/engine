"""
Tests for currency conversion and FX metadata in Costing Service.
"""

import pytest
from engines.boq_costing.service import BoQCostingService
from engines.boq_costing.models import CostRequest, Currency
from engines.boq_costing.catalog import create_default_catalog
from engines.boq_quantities.models import BoQModel, BoQItem, UnitType, Scope

def create_mock_boq() -> BoQModel:
    """Create a simple BoQ model."""
    items = [
        BoQItem(
            id="item1", element_type="wall", quantity=10.0, unit=UnitType.M2,
            scope_id="s1", formula_used="wall_area"
        )
    ]
    scopes = [Scope(scope_id="s1", scope_name="L1", item_count=1)]
    return BoQModel(semantic_model_id="sem1", items=items, scopes=scopes)

class TestCostingCurrency:
    
    def test_currency_conversion_usd_to_gbp(self):
        """Test converting default USD catalog to GBP."""
        service = BoQCostingService()
        boq = create_mock_boq()
        
        # Default Catalog: Wall = $150/m2
        # FX: GBP/USD = 1.27 (meaning 1 GBP = 1.27 USD, so 1 USD = 1/1.27 GBP = 0.7874 GBP)
        # Wait, let's check catalog.py definition of "GBP/USD".
        # catalog.py: "GBP/USD": 1.27. Usually this means 1 GBP = 1.27 USD.
        # So convert USD -> GBP: amount / 1.27.
        
        req = CostRequest(
            boq_model_id=boq.id,
            catalog_version="1.0.0",
            currency=Currency.GBP
        )
        
        cost_model, _ = service.estimate_costs(boq, req)
        
        assert cost_model.currency == Currency.GBP
        
        # Verify Base Cost (USD)
        # 10m2 * $150 = $1500
        assert cost_model.meta["base_currency"] == "USD"
        assert cost_model.meta["total_cost_base"] == 1500.0
        
        # Verify Target Cost (GBP)
        # 1500 / 1.27 = 1181.10
        expected_gbp = round(1500.0 / 1.27, 2)
        assert cost_model.total_cost == expected_gbp
        assert cost_model.meta["total_cost_target"] == expected_gbp
        
        # Verify Metadata
        assert "fx_rate_used" in cost_model.meta
        # Rate used should be approx 1/1.27 = 0.7874
        assert 0.78 < cost_model.meta["fx_rate_used"] < 0.79
        assert cost_model.meta["target_currency"] == "GBP"

    def test_no_conversion_usd_to_usd(self):
        """Test same currency request."""
        service = BoQCostingService()
        boq = create_mock_boq()
        
        req = CostRequest(
            boq_model_id=boq.id,
            catalog_version="1.0.0",
            currency=Currency.USD
        )
        
        cost_model, _ = service.estimate_costs(boq, req)
        
        # 10m2 * $150 = $1500
        assert cost_model.total_cost == 1500.0
        
        # Metadata check
        assert cost_model.meta["base_currency"] == "USD"
        assert cost_model.meta["target_currency"] == "USD"
        # fx_rate_used might not be present or logic dependent
        assert "fx_rate_used" not in cost_model.meta
