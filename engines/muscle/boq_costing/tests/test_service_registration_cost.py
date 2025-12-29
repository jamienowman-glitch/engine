"""
Tests for Cost Service artifact registration.
"""

import pytest
from engines.boq_costing.service import BoQCostingService
from engines.boq_costing.models import CostModel, Currency, CostItem

def mock_cost_model() -> CostModel:
    return CostModel(
        boq_model_id="boq1",
        currency=Currency.GBP,
        catalog_version="1.0.0",
        total_cost=1500.0,
        model_hash="abc123hash",
        items=[CostItem(
            id="c1", boq_item_id="b1", boq_item_type="wall", boq_item_quantity=10, 
            boq_item_unit="m2", unit_rate=150, extended_cost=1500,
            currency=Currency.GBP
        )],
        meta={
            "base_currency": "USD",
            "total_cost_base": 1200.0
        }
    )

def test_register_compliant_artifact():
    """Test successful registration with all fields."""
    service = BoQCostingService()
    model = mock_cost_model()
    
    # helper context
    ctx = {"tenant_id": "t1", "env": "dev"}
    
    artifact_id = service.register_artifact("boq1", model, context=ctx)
    assert "cost_boq1_" in artifact_id

def test_register_validation_failure():
    """Test failure when model meta is incomplete (e.g. if logic was buggy)."""
    service = BoQCostingService()
    model = mock_cost_model()
    # FORCE remove critical data to trigger validation error in register_artifact
    del model.meta["base_currency"] 
    
    ctx = {"tenant_id": "t1", "env": "dev"}
    
    with pytest.raises(ValueError, match="Cost artifact metadata validation failed"):
        service.register_artifact("boq1", model, context=ctx)
