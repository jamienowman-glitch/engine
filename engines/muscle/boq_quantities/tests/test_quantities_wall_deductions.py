"""
Tests for wall quantity deductions (openings).
"""

import pytest
from engines.cad_semantics.models import SemanticElement, SemanticModel, SemanticType, Level
from engines.boq_quantities.formulas import WallFormula, bboxes_intersect

def create_elem(id: str, type: SemanticType, level_id: str, x: float, y: float, w: float, h: float = 2700.0) -> SemanticElement:
    """Create a mock element with geometry ref."""
    # geometry_ref conventions used in formulas:
    # Wall: length, height
    # Window: width, height
    geo = {
        "x": x, "y": y, "z": 0.0,
    }
    if type == SemanticType.WALL:
        geo["length"] = w
        geo["height"] = h
    else:
        geo["width"] = w
        geo["height"] = h
        
    return SemanticElement(
        id=id, cad_entity_id=f"cad_{id}", semantic_type=type, layer="L",
        geometry_ref=geo, level_id=level_id
    )

class TestWallDeductions:
    
    def test_bboxes_intersect_logic(self):
        """Test the helper bbox intersection (centroid distance heuristic)."""
        # Wall at 0,0 length 10m (10000mm)
        w1_geo = {"x": 0, "y": 0, "length": 10000}
        
        # Window at 0,0 width 1m (1000mm) -> Intersects
        win1_geo = {"x": 0, "y": 0, "width": 1000}
        assert bboxes_intersect(w1_geo, win1_geo)
        
        # Window at 20m away -> No intersect
        win2_geo = {"x": 20000, "y": 0, "width": 1000}
        assert not bboxes_intersect(w1_geo, win2_geo)

    def test_deduct_only_intersecting_openings(self):
        """Verify only spatially relevant windows are deducted."""
        # Wall A: 10m long, 3m high -> 30m2
        wall_a = create_elem("wa", SemanticType.WALL, "L1", x=0, y=0, w=10000, h=3000)
        
        # Wall B: 10m long, 3m high -> 30m2 (Far away)
        wall_b = create_elem("wb", SemanticType.WALL, "L1", x=100000, y=0, w=10000, h=3000)
        
        # Window A: 2m x 2m -> 4m2 (Inside Wall A)
        win_a = create_elem("win_a", SemanticType.WINDOW, "L1", x=0, y=0, w=2000, h=2000)
        
        # Window B: 1m x 2m -> 2m2 (Inside Wall B)
        win_b = create_elem("win_b", SemanticType.WINDOW, "L1", x=100000, y=0, w=1000, h=2000)
        
        model = SemanticModel(
            cad_model_id="m1", 
            elements=[wall_a, wall_b, win_a, win_b],
            levels=[Level(id="L1", name="L1", elevation=0, index=0)]
        )
        
        # Test Wall A Calculation
        qty_a, unit_a, type_a, meta_a = WallFormula.calculate(wall_a, model, {})
        assert meta_a["gross_area_m2"] == 30.0
        assert meta_a["opening_area_m2"] == 4.0 # Only win_a
        assert meta_a["net_area_m2"] == 26.0
        assert meta_a["opening_deduction_count"] == 1
        
        # Test Wall B Calculation
        qty_b, unit_b, type_b, meta_b = WallFormula.calculate(wall_b, model, {})
        assert meta_b["gross_area_m2"] == 30.0
        assert meta_b["opening_area_m2"] == 2.0 # Only win_b
        assert meta_b["net_area_m2"] == 28.0
        assert meta_b["opening_deduction_count"] == 1
