"""
DXF Adapter - Parse DXF files and normalize to CadModel.

Handles:
- Stream parsing of DXF entities
- Unit detection and conversion
- Layer extraction
- Deterministic ID generation
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

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


def parse_dxf_content(content: bytes) -> Dict[str, Any]:
    """
    Parse DXF file content (simplified stream parser).
    For production, consider ezdxf library.
    
    Returns dict with:
    - 'layers': List[dict] with name, color
    - 'entities': List[dict] with type, layer, geometry
    - 'units': str like 'mm', 'cm', etc. or None
    """
    # For MVP, we do basic text-based parsing
    # In production, use: import ezdxf
    
    text = content.decode("utf-8", errors="ignore")
    lines = text.split("\n")
    
    result: Dict[str, Any] = {
        "layers": [],
        "entities": [],
        "units": None,
    }
    
    current_section = None
    i = 0
    seen_layers = set()
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line == "SECTION":
            i += 1
            if i < len(lines):
                section_type = lines[i].strip()
                if section_type == "2":
                    i += 1
                    if i < len(lines):
                        current_section = lines[i].strip()
        
        # Extract UNITS (HEADER section)
        elif current_section == "HEADER" and line == "9":
            i += 1
            if i < len(lines) and "$UNITS" in lines[i]:
                i += 1
                if i < len(lines) and lines[i].strip() == "70":
                    i += 1
                    if i < len(lines):
                        units_code = int(lines[i].strip())
                        result["units"] = _units_from_code(units_code)
        
        # Extract LAYER definitions (TABLES section)
        elif current_section == "TABLES" and line == "LAYER":
            # Parse layer entry
            layer_info = _parse_layer_entry(lines, i)
            if layer_info and layer_info["name"] not in seen_layers:
                result["layers"].append(layer_info)
                seen_layers.add(layer_info["name"])
            i += 1
        
        # Extract ENTITIES (ENTITIES section)
        elif current_section == "ENTITIES" and line in ("LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE", "SOLID"):
            entity_info = _parse_entity_entry(lines, i)
            if entity_info:
                result["entities"].append(entity_info)
        
        i += 1
    
    return result


def _units_from_code(code: int) -> Optional[str]:
    """Map DXF units code to UnitKind."""
    mapping = {
        0: None,  # Unitless
        1: "in",  # Inches
        2: "ft",  # Feet
        4: "mm",  # Millimeters
        5: "cm",  # Centimeters
        6: "m",   # Meters
    }
    return mapping.get(code)


def _parse_layer_entry(lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
    """Parse a LAYER table entry from DXF lines."""
    layer_info = {"name": "Default", "color": None}
    i = start_idx + 1  # Start after "LAYER"
    
    while i < len(lines) and i < start_idx + 50:
        line = lines[i].strip()
        
        # Stop at end markers
        if line in ("ENDTAB", "LAYER"):
            break
        
        # Layer name is after "2" tag
        if line == "2":
            i += 1
            if i < len(lines):
                layer_info["name"] = lines[i].strip()
        
        # Color code is after "62" tag
        if line == "62":
            i += 1
            if i < len(lines):
                try:
                    layer_info["color"] = int(lines[i].strip())
                except ValueError:
                    pass
        
        i += 1
    
    return layer_info


def _parse_entity_entry(lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
    """Parse an ENTITY entry from DXF lines (simplified)."""
    if start_idx >= len(lines):
        return None
    
    line = lines[start_idx].strip()
    
    # Only process if this line is an entity type
    if line not in ("LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE", "SOLID"):
        return None
    
    entity_type = line
    layer = "0"
    geometry: Dict[str, Any] = {}
    source_id = None
    i = start_idx + 1

    # Parse entity properties
    while i < len(lines) and i < start_idx + 100:
        line = lines[i].strip()
        
        # Stop at next entity or section end
        if line in ("ENDSEC", "ENDBLK", "LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE", "SOLID"):
            break
        
        if line == "5":  # Handle (ID)
            i += 1
            if i < len(lines):
                source_id = lines[i].strip()
        
        if line == "8":  # Layer
            i += 1
            if i < len(lines):
                layer = lines[i].strip()
        
        if line == "10":  # X coordinate (common)
            geometry["x"] = _parse_float(lines, i)
        if line == "20":  # Y coordinate
            geometry["y"] = _parse_float(lines, i)
        if line == "30":  # Z coordinate
            geometry["z"] = _parse_float(lines, i)
        
        if line == "40":  # Radius for circles/arcs
            geometry["radius"] = _parse_float(lines, i)
        
        i += 1
    
    return {
        "type": entity_type,
        "layer": layer,
        "source_id": source_id,
        "geometry": geometry,
    }


def _parse_float(lines: List[str], idx: int) -> float:
    """Parse next line as float."""
    if idx + 1 < len(lines):
        try:
            return float(lines[idx + 1].strip())
        except ValueError:
            return 0.0
    return 0.0


def _dxf_type_to_entity_type(dxf_type: str) -> EntityType:
    """Map DXF type string to EntityType."""
    mapping = {
        "LINE": EntityType.LINE,
        "CIRCLE": EntityType.CIRCLE,
        "ARC": EntityType.ARC,
        "LWPOLYLINE": EntityType.POLYLINE,
        "POLYLINE": EntityType.POLYLINE,
        "SOLID": EntityType.SOLID,
    }
    return mapping.get(dxf_type, EntityType.SOLID)


def _compute_bbox_for_geometry(entity_type: EntityType, geometry: Dict[str, Any]) -> BoundingBox:
    """Compute bounding box for entity geometry."""
    x = geometry.get("x", 0.0)
    y = geometry.get("y", 0.0)
    z = geometry.get("z", 0.0)
    radius = geometry.get("radius", 0.0)
    
    min_pt = Vector3(x=x - radius, y=y - radius, z=z)
    max_pt = Vector3(x=x + radius, y=y + radius, z=z)
    return BoundingBox(min=min_pt, max=max_pt)


def _deterministic_entity_id(
    source_id: Optional[str], entity_type: str, layer: str, geometry: Dict[str, Any]
) -> str:
    """Generate deterministic ID based on geometry + layer + source."""
    combined = f"{entity_type}:{layer}:{geometry}"
    if source_id:
        combined = f"{source_id}:{combined}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def dxf_to_cad_model(
    content: bytes,
    unit_hint: Optional[UnitKind] = None,
    tolerance: float = 0.001,
) -> CadModel:
    """
    Parse DXF file and convert to CadModel.
    
    Args:
        content: DXF file bytes
        unit_hint: Override detected units
        tolerance: Healing tolerance
    
    Returns:
        CadModel with entities, layers, and topology
    """
    parsed = parse_dxf_content(content)
    
    # Determine units
    units = unit_hint
    if not units:
        detected = parsed.get("units")
        if detected:
            units = UnitKind(detected)
        else:
            # DXF file missing unit specification; ambiguous
            raise ValueError(
                "DXF file missing unit specification ($UNITS); provide unit_hint "
                "(mm|cm|m|ft|in)"
            )
    
    # Extract layers
    layers = []
    for layer_dict in parsed.get("layers", []):
        layer = Layer(
            name=layer_dict.get("name", "Default"),
            visible=True,
            color=f"#{layer_dict.get('color', 0):06X}" if layer_dict.get("color") else None,
        )
        layers.append(layer)
    
    # Convert entities
    entities = []
    entity_bboxes = []
    
    for ent_dict in parsed.get("entities", []):
        ent_type = _dxf_type_to_entity_type(ent_dict.get("type", "SOLID"))
        layer = ent_dict.get("layer", "0")
        source_id = ent_dict.get("source_id")
        geometry = ent_dict.get("geometry", {})
        
        bbox = _compute_bbox_for_geometry(ent_type, geometry)
        entity_bboxes.append(bbox)
        
        entity_id = _deterministic_entity_id(source_id, ent_dict.get("type"), layer, geometry)
        
        entity = Entity(
            id=entity_id,
            type=ent_type,
            layer=layer,
            source_id=source_id,
            geometry=geometry,
            bbox=bbox,
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
        source_format="dxf",
        source_sha256=hashlib.sha256(content).hexdigest(),
        tolerance=tolerance,
    )
    
    # Compute model hash
    model_repr = f"{model.units}:{model.bbox}:{len(model.entities)}:{len(model.layers)}"
    model.model_hash = hashlib.sha256(model_repr.encode()).hexdigest()[:16]
    
    return model
