"""
Tests for default costing behavior (Catalog 1.0.0).
"""

import pytest
from engines.boq_costing.service import BoQCostingService
from engines.boq_costing.models import CostRequest, Currency
from engines.boq_quantities.models import BoQModel, BoQItem, UnitType, Scope

def create_mock_boq() -> BoQModel:
    """Create a simple BoQ model."""
    items = [
        BoQItem(
            id="item1", element_type="wall", quantity=10.0, unit=UnitType.M2,
            scope_id="s1", formula_used="wall_area"
        ),
        BoQItem(
            id="item2", element_type="door", quantity=2.0, unit=UnitType.COUNT,
            scope_id="s1", formula_used="door_count"
        ),
    ]
    scopes = [Scope(scope_id="s1", scope_name="L1", item_count=2)]
    
    return BoQModel(semantic_model_id="sem1", items=items, scopes=scopes)

class TestCostingDefaults:
    
    def test_default_catalog_pricing(self):
        """Test pricing using default 1.0.0 catalog."""
        service = BoQCostingService()
        boq = create_mock_boq()
        
        req = CostRequest(
            boq_model_id=boq.id,
            catalog_version="1.0.0",
            currency=Currency.USD
        )
        
        cost_model, _ = service.estimate_costs(boq, req)
        
        assert cost_model.catalog_version == "1.0.0"
        assert len(cost_model.items) == 2
        
        # Wall: 10m2 * $150 (default) = $1500
        wall_item = next(i for i in cost_model.items if i.boq_item_type == "wall")
        assert wall_item.extended_cost == 1500.0
        
        # Door: 2 * $800 = $1600
        door_item = next(i for i in cost_model.items if i.boq_item_type == "door")
        assert door_item.extended_cost == 1600.0
        
        # Total: 3100
        assert cost_model.total_cost == 3100.0

    def test_unknown_version_error(self):
        """Test error on unknown catalog version."""
        service = BoQCostingService()
        boq = create_mock_boq()
        
        req = CostRequest(boq_model_id=boq.id, catalog_version="99.9.9")
        
        with pytest.raises(ValueError, match="Catalog version '99.9.9' not found"):
            service.estimate_costs(boq, req)
