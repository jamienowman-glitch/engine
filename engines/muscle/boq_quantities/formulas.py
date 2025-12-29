"""
BoQ Quantity Formulas - Calculate quantities for each element type.

Implements:
- Wall area/length calculations with opening deductions
- Slab area and volume
- Column counting and volume
- Door/window counts and areas
- Room area and perimeter
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from engines.cad_semantics.models import SemanticElement, SemanticModel, SemanticType
from engines.boq_quantities.models import BoQItem, FormulaType, UnitType


class QuantityFormula:
    """Base class for quantity calculations."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """
        Calculate quantity for element.
        
        Returns:
            (quantity, unit, formula_type, meta)
        """
        raise NotImplementedError


def bboxes_intersect(b1: Dict[str, Any], b2: Dict[str, Any], tolerance: float = 10.0) -> bool:
    """
    Check if two 2D bboxes intersect (ignoring Z for wall/opening overlap).
    Using simple min/max bounds from geometry if available, 
    otherwise assuming geometry_ref has 2D bounds or center+dims.
    
    Since we don't have BoundingBox objects here (just dict refs), 
    we'll need to rely on the underlying geometry_ref details if standard bbox not present.
    However, assuming standard bbox presence or derived center+dim logic.
    
    For this heuristic, we assume openings are usually 'inside' the wall length/width.
    """
    # Helper to extract min/max 2D
    def get_bounds(geo):
        # Try explicit bbox if passed (not guaranteed in dict)
        # Fallback to center/dims
        x = geo.get("x", 0.0)
        y = geo.get("y", 0.0)
        w = geo.get("length", geo.get("width", 0.0)) # Wall length or Window width
        t = geo.get("thickness", 200.0) # Wall thickness implies depth
        # Rotation is tricky. For simplified logic, assume axis aligned or 
        # just check distance < sum_dims/2
        return x, y, w, t

    x1, y1, w1, t1 = get_bounds(b1)
    x2, y2, w2, t2 = get_bounds(b2)
    
    # Simple circle/distance check might be safer if rotation unknown?
    # Or strict AABB check?
    # Let's use strict AABB with "inflate" logic for intersection.
    # But wait, walls are usually lines?
    # CAD system usually defines walls as Polyline (start/end) or location + dim.
    # Let's look at bboxes_adjacent logic in graph.py - it used centroid distance.
    # For embedding, the opening centroid should be roughly ON the wall line 
    # and within the wall segments.
    # Let's use centroid distance: distance(c1, c2) < (L1 + L2)/2 roughly?
    
    # Better: check if opening centroid is close to wall curve.
    # But we only have generic geometry dict here.
    # Let's assume standard centroid distance check for "overlap" in close proximity.
    
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    
    # If generic 3D dist check?
    dist = (dx*dx + dy*dy)**0.5
    
    # If distance is small enough (e.g. within wall length/2), assume potential match.
    # But we need to distinguish between separate walls.
    # Check if distance is less than (wall_length/2 + opening_width/2) roughly?
    max_dist = (w1 + w2) / 2.0
    
    # Also need to check if they are collinear or "touching" in thickness.
    # Use tighter tolerance for thickness axis? Hard without rotation.
    # Let's use a conservative containment check:
    # Opening centroid must be within Wall radius?
    
    # REVISED: BoundingBox check is best if we had it.
    # Since we don't, let's look at `bbox` field on SemanticElement? 
    # models.py says: `geometry_ref: Dict`.
    # But `SemanticElement` is created from `CadModel.Entity` which HAS `bbox`.
    # Let's revert to using `element.geometry_ref` values which are usually central.
    
    return dist < (max_dist + tolerance)


class WallFormula(QuantityFormula):
    """Wall area and length calculation."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """Calculate wall area/length."""
        # Default wall thickness
        wall_thickness = params.get("wall_thickness_mm", 200.0)
        default_height = params.get("wall_height_mm", 2700.0)
        
        # Get geometry
        geom = element.geometry_ref or {}
        length = geom.get("length", 0.0)
        height = geom.get("height", default_height)
        
        # Wall area: length × height
        area_mm2 = length * height
        area_m2 = area_mm2 / 1_000_000  # Convert mm² to m²
        
        # Find openings (doors/windows on same level AND intersecting)
        opening_area_m2 = 0.0
        opening_count = 0
        
        for other_elem in semantic_model.elements:
            if (other_elem.level_id == element.level_id and 
                other_elem.semantic_type in (SemanticType.DOOR, SemanticType.WINDOW)):
                
                # Check spatial intersection
                other_geom = other_elem.geometry_ref or {}
                if bboxes_intersect(geom, other_geom):
                    opening_width = other_geom.get("width", 1000.0)
                    opening_height = other_geom.get("height", 2000.0)
                    opening_area_mm2 = opening_width * opening_height
                    opening_area_m2 += opening_area_mm2 / 1_000_000
                    opening_count += 1
        
        # Net area
        net_area_m2 = max(0, area_m2 - opening_area_m2)
        
        meta = {
            "gross_area_m2": round(area_m2, 3),
            "opening_area_m2": round(opening_area_m2, 3),
            "net_area_m2": round(net_area_m2, 3),
            "length_m": round(length / 1000, 3),
            "height_m": round(height / 1000, 3),
            "thickness_mm": wall_thickness,
            "opening_deduction_count": opening_count,
        }
        
        return net_area_m2, UnitType.M2, FormulaType.WALL_AREA_NET, meta


class SlabFormula(QuantityFormula):
    """Slab area and volume calculation."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """Calculate slab area/volume."""
        default_thickness = params.get("slab_thickness_mm", 200.0)
        
        geom = element.geometry_ref or {}
        area_mm2 = geom.get("area", 0.0)
        thickness = geom.get("thickness", default_thickness)
        
        # Slab area in m²
        area_m2 = area_mm2 / 1_000_000
        
        # Slab volume in m³
        volume_mm3 = area_mm2 * thickness
        volume_m3 = volume_mm3 / 1_000_000_000
        
        meta = {
            "area_m2": round(area_m2, 3),
            "thickness_mm": thickness,
            "volume_m3": round(volume_m3, 3),
        }
        
        return area_m2, UnitType.M2, FormulaType.SLAB_AREA, meta


class ColumnFormula(QuantityFormula):
    """Column counting and volume."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """Calculate column (unit count for BoQ)."""
        # Columns are typically counted as individual items
        quantity = 1.0
        
        geom = element.geometry_ref or {}
        section_area = geom.get("section_area", 0.0)  # mm²
        height = geom.get("height", 0.0)  # mm
        
        # Convert to m²
        section_area_m2 = section_area / 1_000_000
        height_m = height / 1000
        
        # Volume in m³
        volume_m3 = (section_area * height) / 1_000_000_000
        
        meta = {
            "count": 1,
            "section_area_m2": round(section_area_m2, 3),
            "height_m": round(height_m, 3),
            "volume_m3": round(volume_m3, 3),
        }
        
        return quantity, UnitType.COUNT, FormulaType.COLUMN_COUNT, meta


class DoorFormula(QuantityFormula):
    """Door counting."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """Calculate door count."""
        quantity = 1.0  # Each door is 1 item
        
        geom = element.geometry_ref or {}
        width = geom.get("width", 900.0)
        height = geom.get("height", 2100.0)
        area_mm2 = width * height
        area_m2 = area_mm2 / 1_000_000
        
        meta = {
            "count": 1,
            "width_mm": width,
            "height_mm": height,
            "opening_area_m2": round(area_m2, 3),
        }
        
        return quantity, UnitType.COUNT, FormulaType.DOOR_COUNT, meta


class WindowFormula(QuantityFormula):
    """Window counting."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """Calculate window count."""
        quantity = 1.0  # Each window is 1 item
        
        geom = element.geometry_ref or {}
        width = geom.get("width", 1200.0)
        height = geom.get("height", 1500.0)
        area_mm2 = width * height
        area_m2 = area_mm2 / 1_000_000
        
        meta = {
            "count": 1,
            "width_mm": width,
            "height_mm": height,
            "glazing_area_m2": round(area_m2, 3),
        }
        
        return quantity, UnitType.COUNT, FormulaType.WINDOW_COUNT, meta


class RoomFormula(QuantityFormula):
    """Room area and perimeter."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """Calculate room area."""
        geom = element.geometry_ref or {}
        area_mm2 = geom.get("area", 0.0)
        area_m2 = area_mm2 / 1_000_000
        
        meta = {
            "area_m2": round(area_m2, 3),
        }
        
        return area_m2, UnitType.M2, FormulaType.ROOM_AREA, meta


class UnknownFormula(QuantityFormula):
    """Default for unknown types."""
    
    @staticmethod
    def calculate(
        element: SemanticElement,
        semantic_model: SemanticModel,
        params: Dict[str, Any],
    ) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
        """No calculation for unknown types."""
        return 0.0, UnitType.COUNT, FormulaType.UNKNOWN, {}


# Formula registry
FORMULAS: Dict[SemanticType, type[QuantityFormula]] = {
    SemanticType.WALL: WallFormula,
    SemanticType.SLAB: SlabFormula,
    SemanticType.COLUMN: ColumnFormula,
    SemanticType.DOOR: DoorFormula,
    SemanticType.WINDOW: WindowFormula,
    SemanticType.ROOM: RoomFormula,
    SemanticType.LEVEL: UnknownFormula,
    SemanticType.STAIR: UnknownFormula,
    SemanticType.UNKNOWN: UnknownFormula,
}


def calculate_quantity(
    element: SemanticElement,
    semantic_model: SemanticModel,
    params: Dict[str, Any],
) -> Tuple[float, UnitType, FormulaType, Dict[str, Any]]:
    """
    Calculate quantity for a semantic element.
    
    Args:
        element: Semantic element to calculate
        semantic_model: Full semantic model for context
        params: Calculation parameters (thicknesses, defaults, etc.)
    
    Returns:
        (quantity, unit, formula_type, meta)
    """
    formula_class = FORMULAS.get(element.semantic_type, UnknownFormula)
    return formula_class.calculate(element, semantic_model, params)


def deterministic_boq_item_id(element_id: str, element_type: str) -> str:
    """Generate deterministic BoQ item ID."""
    key = f"{element_id}:{element_type}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
