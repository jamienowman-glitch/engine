"""Tests for CadOverlayView generation from boq_costing engine."""
from unittest.mock import Mock

from engines.cad_viewer.service import CadViewerService, MissingArtifactError
from engines.boq_costing.models import CostModel, CostItem, Currency


def _make_cost_item(item_id: str, name: str, quantity: float, unit: str, total_cost: float) -> CostItem:
    """Create a CostItem fixture."""
    unit_rate = total_cost / quantity if quantity > 0 else 0.0
    return CostItem(
        id=item_id,
        boq_item_id=f"boq-{item_id}",
        boq_item_type="wall",
        boq_item_quantity=quantity,
        boq_item_unit=unit,
        name=name,
        quantity=quantity,
        unit=unit,
        cost=total_cost,
        total_cost=total_cost,
        unit_rate=unit_rate,
        extended_cost=total_cost,
        currency=Currency.USD,
        calc_version="1.0.0",
        meta={},
    )


def _make_cost_model(item_count: int = 2) -> CostModel:
    """Create a CostModel fixture."""
    items = [
        _make_cost_item("item-1", "Exterior Wall", 50.0, "m2", 50000.0),
        _make_cost_item("item-2", "Floor Slab", 100.0, "m2", 50000.0),
    ]
    if item_count > 2:
        for i in range(2, item_count):
            items.append(_make_cost_item(f"item-{i+1}", f"Element {i}", 10.0, "unit", 5000.0))
    
    model = CostModel(
        id="cost-test-001",
        boq_model_id="boq-001",
        currency=Currency.USD,
        items=items,
        total_cost=100000.0 + (item_count - 2) * 5000.0,
    )
    return model


def test_build_overlay_view_success():
    """Test successful overlay view generation from cost model."""
    # Create mock costing service
    cost_model = _make_cost_model(item_count=2)
    mock_cost_svc = Mock()
    mock_cost_svc.get_cost_model.return_value = cost_model
    
    # Create service with mocked dependency
    svc = CadViewerService(costing_service=mock_cost_svc)
    
    # Build overlay view
    view = svc.build_overlay_view(
        project_id="proj-001",
        cost_model_id="cost-001",
        context={"tenant_id": "tenant-test", "env": "dev", "request_id": "req-456"},
    )
    
    # Assert view structure
    assert view.project_id == "proj-001"
    assert view.cad_model_id == "cost-001"
    assert len(view.elements) == 2
    assert view.elements[0].name == "boq-item-1"  # boq_item_id is used as name
    assert view.elements[1].name == "boq-item-2"
    assert view.elements[0].quantity == 50.0
    assert view.elements[1].quantity == 100.0
    
    # Assert costs
    assert view.elements[0].cost == 50000.0
    assert view.elements[1].cost == 50000.0
    
    # Assert deterministic hashes
    assert view.view_hash is not None
    assert view.elements[0].hash is not None
    assert view.elements[1].hash is not None
    
    # Assert request context propagated
    assert view.meta.get("tenant_id") == "tenant-test"
    assert view.meta.get("env") == "dev"
    assert view.meta.get("request_id") == "req-456"


def test_build_overlay_view_missing_cost_model():
    """Test error when cost_model is missing."""
    # Create mock costing service that returns None
    mock_cost_svc = Mock()
    mock_cost_svc.get_cost_model.return_value = None
    
    svc = CadViewerService(costing_service=mock_cost_svc)
    
    # Should raise MissingArtifactError
    try:
        svc.build_overlay_view(project_id="proj-001", cost_model_id="cost-001")
        assert False, "Expected MissingArtifactError"
    except MissingArtifactError as e:
        assert "cost_model" in e.missing_kinds


def test_build_overlay_view_determinism():
    """Test that same inputs produce identical hashes."""
    cost_model = _make_cost_model(item_count=2)
    mock_cost_svc = Mock()
    mock_cost_svc.get_cost_model.return_value = cost_model
    
    svc = CadViewerService(costing_service=mock_cost_svc)
    
    # Generate view twice with same inputs
    view1 = svc.build_overlay_view(project_id="proj-001", cost_model_id="cost-001")
    view2 = svc.build_overlay_view(project_id="proj-001", cost_model_id="cost-001")
    
    # Hashes should match
    assert view1.view_hash == view2.view_hash
    assert view1.elements[0].hash == view2.elements[0].hash
    assert view1.elements[1].hash == view2.elements[1].hash


def test_build_overlay_view_quantity_and_cost_aggregation():
    """Test that elements correctly expose quantity and cost."""
    cost_model = _make_cost_model(item_count=2)
    mock_cost_svc = Mock()
    mock_cost_svc.get_cost_model.return_value = cost_model
    
    svc = CadViewerService(costing_service=mock_cost_svc)
    view = svc.build_overlay_view(project_id="proj-001", cost_model_id="cost-001")
    
    # Wall element
    assert view.elements[0].quantity == 50.0
    assert view.elements[0].unit == "m2"
    assert view.elements[0].cost == 50000.0
    
    # Floor element
    assert view.elements[1].quantity == 100.0
    assert view.elements[1].unit == "m2"
    assert view.elements[1].cost == 50000.0
