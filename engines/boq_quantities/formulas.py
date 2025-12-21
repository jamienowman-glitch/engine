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
        
        # Find openings (doors/windows on same level)
        opening_area_m2 = 0.0
        for other_elem in semantic_model.elements:
            if (other_elem.level_id == element.level_id and 
                other_elem.semantic_type in (SemanticType.DOOR, SemanticType.WINDOW)):
                other_geom = other_elem.geometry_ref or {}
                opening_width = other_geom.get("width", 1000.0)
                opening_height = other_geom.get("height", 2000.0)
                opening_area_mm2 = opening_width * opening_height
                opening_area_m2 += opening_area_mm2 / 1_000_000
        
        # Net area
        net_area_m2 = max(0, area_m2 - opening_area_m2)
        
        meta = {
            "gross_area_m2": round(area_m2, 3),
            "opening_area_m2": round(opening_area_m2, 3),
            "net_area_m2": round(net_area_m2, 3),
            "length_m": round(length / 1000, 3),
            "height_m": round(height / 1000, 3),
            "thickness_mm": wall_thickness,
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
