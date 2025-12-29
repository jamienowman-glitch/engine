"""
IFC-lite Adapter - Parse simplified IFC files and normalize to CadModel.

Handles:
- Stream parsing of IFC-lite (minimal subset: walls, slabs, windows, doors)
- Unit detection
- Placement transform handling
- Entity conversion
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from engines.cad_ingest.models import (
    BoundingBox,
    CadModel,
    Entity,
    EntityType,
    Layer,
    TopologyGraph,
    UnitKind,
    Vector3,
)


def parse_ifc_lite_content(content: bytes) -> Dict[str, Any]:
    """
    Parse IFC-lite file content (JSON-based simplified IFC format).
    
    Returns dict with:
    - 'units': str like 'mm', 'cm', etc. or None
    - 'elements': List[dict] with type, layer, geometry, placement
    - 'layers': List[dict] with name
    """
    text = content.decode("utf-8", errors="ignore")
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback to simple line-based parsing
        data = _parse_ifc_lite_text(text)
    
    return data


def _parse_ifc_lite_text(text: str) -> Dict[str, Any]:
    """Parse IFC-lite from text lines (fallback)."""
    result: Dict[str, Any] = {
        "units": None,
        "elements": [],
        "layers": [],
    }
    
    lines = text.split("\n")
    current_element = None
    seen_layers = set()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse simple key=value pairs
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            
            if key == "UNIT":
                result["units"] = val
            elif key == "ELEMENT_TYPE":
                if current_element:
                    result["elements"].append(current_element)
                current_element = {"type": val, "layer": "Default", "geometry": {}, "placement": {}}
            elif key == "LAYER" and current_element:
                current_element["layer"] = val
                if val not in seen_layers:
                    result["layers"].append({"name": val})
                    seen_layers.add(val)
            elif key in ("X", "Y", "Z") and current_element:
                try:
                    current_element["geometry"][key.lower()] = float(val)
                except ValueError:
                    pass
            elif key in ("WIDTH", "HEIGHT", "LENGTH") and current_element:
                try:
                    current_element["geometry"][key.lower()] = float(val)
                except ValueError:
                    pass
    
    if current_element:
        result["elements"].append(current_element)
    
    return result


def _ifc_type_to_entity_type(ifc_type: str) -> EntityType:
    """Map IFC element type to EntityType."""
    ifc_type_lower = ifc_type.lower()
    
    if "wall" in ifc_type_lower:
        return EntityType.SOLID
    elif "slab" in ifc_type_lower or "floor" in ifc_type_lower:
        return EntityType.SOLID
    elif "window" in ifc_type_lower or "door" in ifc_type_lower:
        return EntityType.SOLID
    elif "column" in ifc_type_lower or "beam" in ifc_type_lower:
        return EntityType.SOLID
    else:
        return EntityType.SOLID


def _apply_placement_transform(
    geometry: Dict[str, Any], placement: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply placement (location + rotation) to geometry.
    For MVP, just shift by location.
    """
    result = dict(geometry)
    
    loc = placement.get("location", {})
    x_offset = loc.get("x", 0.0)
    y_offset = loc.get("y", 0.0)
    z_offset = loc.get("z", 0.0)
    
    if "x" in result:
        result["x"] = float(result["x"]) + x_offset
    else:
        result["x"] = x_offset
    
    if "y" in result:
        result["y"] = float(result["y"]) + y_offset
    else:
        result["y"] = y_offset
    
    if "z" in result:
        result["z"] = float(result["z"]) + z_offset
    else:
        result["z"] = z_offset
    
    return result


def _compute_bbox_from_geometry(geometry: Dict[str, Any]) -> BoundingBox:
    """Compute bbox for IFC element."""
    x = float(geometry.get("x", 0.0))
    y = float(geometry.get("y", 0.0))
    z = float(geometry.get("z", 0.0))
    
    width = float(geometry.get("width", 1.0))
    height = float(geometry.get("height", 1.0))
    length = float(geometry.get("length", 1.0))
    
    min_pt = Vector3(x=x - width / 2, y=y - height / 2, z=z)
    max_pt = Vector3(x=x + width / 2, y=y + height / 2, z=z + length)
    
    return BoundingBox(min=min_pt, max=max_pt)


def _deterministic_ifc_entity_id(
    ifc_type: str, layer: str, geometry: Dict[str, Any]
) -> str:
    """Generate deterministic ID for IFC entity."""
    combined = f"{ifc_type}:{layer}:{geometry}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def ifc_lite_to_cad_model(
    content: bytes,
    unit_hint: Optional[UnitKind] = None,
    tolerance: float = 0.001,
) -> CadModel:
    """
    Parse IFC-lite file and convert to CadModel.
    
    Args:
        content: IFC-lite file bytes (JSON or text)
        unit_hint: Override detected units
        tolerance: Healing tolerance
    
    Returns:
        CadModel with entities, layers, and topology
    
    Raises:
        ValueError: If units are ambiguous/missing and no hint provided
    """
    parsed = parse_ifc_lite_content(content)
    
    # Determine units
    units = unit_hint
    if not units:
        detected = parsed.get("units")
        if detected:
            try:
                units = UnitKind(detected)
            except ValueError:
                units = UnitKind.MILLIMETER
        else:
            # IFC-lite should specify units; missing is error
            raise ValueError(
                "IFC-lite file missing unit specification; provide unit_hint "
                "(mm|cm|m|ft|in)"
            )
    
    # Extract layers
    layers = []
    seen_layers = set()
    
    for layer_dict in parsed.get("layers", []):
        name = layer_dict.get("name", "Default")
        if name not in seen_layers:
            layer = Layer(name=name, visible=True)
            layers.append(layer)
            seen_layers.add(name)
    
    # Ensure at least Default layer
    if "Default" not in seen_layers:
        layers.append(Layer(name="Default"))
    
    # Convert elements to entities
    entities = []
    entity_bboxes = []
    
    for elt_dict in parsed.get("elements", []):
        ifc_type = elt_dict.get("type", "Unknown")
        layer = elt_dict.get("layer", "Default")
        geometry = elt_dict.get("geometry", {})
        placement = elt_dict.get("placement", {})
        
        # Apply placement transform
        geometry = _apply_placement_transform(geometry, placement)
        
        ent_type = _ifc_type_to_entity_type(ifc_type)
        bbox = _compute_bbox_from_geometry(geometry)
        entity_bboxes.append(bbox)
        
        entity_id = _deterministic_ifc_entity_id(ifc_type, layer, geometry)
        
        entity = Entity(
            id=entity_id,
            type=ent_type,
            layer=layer,
            source_id=elt_dict.get("id"),
            geometry=geometry,
            bbox=bbox,
            meta={"ifc_type": ifc_type},
        )
        entities.append(entity)
    
    # Compute overall bbox
    if entity_bboxes:
        min_x = min(b.min.x for b in entity_bboxes)
        min_y = min(b.min.y for b in entity_bboxes)
        min_z = min(b.min.z for b in entity_bboxes)
        max_x = max(b.max.x for b in entity_bboxes)
        max_y = max(b.max.y for b in entity_bboxes)
        max_z = max(b.max.z for b in entity_bboxes)
        bbox = BoundingBox(
            min=Vector3(x=min_x, y=min_y, z=min_z),
            max=Vector3(x=max_x, y=max_y, z=max_z),
        )
    else:
        bbox = BoundingBox(
            min=Vector3(x=0, y=0, z=0),
            max=Vector3(x=1, y=1, z=1),
        )
    
    # Create model
    model = CadModel(
        units=units,
        bbox=bbox,
        layers=layers,
        entities=entities,
        topology=TopologyGraph(),
        source_format="ifc-lite",
        source_sha256=hashlib.sha256(content).hexdigest(),
        tolerance=tolerance,
    )
    
    # Compute model hash
    model_repr = f"{model.units}:{model.bbox}:{len(model.entities)}:{len(model.layers)}"
    model.model_hash = hashlib.sha256(model_repr.encode()).hexdigest()[:16]
    
    return model
