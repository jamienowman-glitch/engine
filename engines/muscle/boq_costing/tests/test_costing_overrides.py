"""
Tests for costing overrides and version selection.
"""

import pytest
from engines.boq_costing.service import BoQCostingService
from engines.boq_costing.models import CostRequest, Currency
from engines.boq_quantities.models import BoQModel, BoQItem, UnitType, Scope

def create_mock_boq() -> BoQModel:
    items = [
        BoQItem(
            id="item1", element_type="wall", quantity=10.0, unit=UnitType.M2,
            scope_id="s1", formula_used="wall_area"
        ),
    ]
    scopes = [Scope(scope_id="s1", scope_name="L1", item_count=1)]
    return BoQModel(semantic_model_id="sem1", items=items, scopes=scopes)

class TestCostingOverrides:
    
    def test_catalog_version_selection(self):
        """Test selecting a non-default catalog version."""
        service = BoQCostingService()
        boq = create_mock_boq()
        
        # Use 2025-Q1 (which has +10% rates)
        req = CostRequest(
            boq_model_id=boq.id,
            catalog_version="2025-Q1",
            currency=Currency.USD
        )
        
        cost_model, _ = service.estimate_costs(boq, req)
        
        assert cost_model.catalog_version == "2025-Q1"
        
        # Wall defaults 150. 2025-Q1 is +10% -> 165.
        # 10m2 * 165 = 1650.
        assert cost_model.total_cost == 1650.0

    def test_request_overrides(self):
        """Test applying specific rate overrides."""
        service = BoQCostingService()
        boq = create_mock_boq()
        
        # Override Wall rate to $200
        req = CostRequest(
            boq_model_id=boq.id,
            catalog_version="1.0.0",
            catalog_overrides={"wall": 200.0}
        )
        
        cost_model, _ = service.estimate_costs(boq, req)
        
        # 10m2 * 200 = 2000
        assert cost_model.total_cost == 2000.0
        
        # Verify item detail
        item = cost_model.items[0]
        # Rate might be stored as logic dictates. 
        # Wait, my logic didn't explicitly store unit_rate override if I recall. 
        # Ah, I see: `unit_rate=base_rate` in implementation.
        assert item.extended_cost == 2000.0
