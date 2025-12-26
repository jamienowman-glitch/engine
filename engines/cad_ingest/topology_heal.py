"""
Topology Healing - Repair and normalize CAD geometry.

Implements:
- Gap closing within tolerance
- Duplicate vertex/entity removal
- Winding normalization for closed polylines
- Validation of healed geometry
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Set, Tuple

from engines.cad_ingest.models import (
    Entity,
    EntityType,
    HealingAction,
    HealingActionKind,
    Vector3,
    BoundingBox,
)


def distance_3d(p1: Vector3, p2: Vector3) -> float:
    """Compute Euclidean distance between two 3D points."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    dz = p1.z - p2.z
    return (dx**2 + dy**2 + dz**2) ** 0.5


def vector_equal(p1: Vector3, p2: Vector3, tolerance: float) -> bool:
    """Check if two points are equal within tolerance."""
    return distance_3d(p1, p2) <= tolerance


def normalize_polygon_winding(vertices: List[Vector3]) -> List[Vector3]:
    """
    Normalize winding order for 2D polygon (assumes Z is constant).
    Uses signed area to determine order; returns counter-clockwise.
    """
    if len(vertices) < 3:
        return vertices

    # Compute signed area
    area = 0.0
    for i in range(len(vertices)):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % len(vertices)]
        area += (v2.x - v1.x) * (v2.y + v1.y)
    
    # Trapezoid formula: sum((x2-x1)(y2+y1))
    # Area > 0 implies Clockwise (assuming Y-up)
    # Area < 0 implies Counter-Clockwise
    
    # We want CCW. If CW (area > 0), reverse.
    if area > 0:
        return list(reversed(vertices))
    return vertices


def close_gaps_in_polyline(
    vertices: List[Vector3], tolerance: float, snap_distance: float = 0.1
) -> Tuple[List[Vector3], List[str]]:
    """
    Close gaps in polyline by snapping nearby endpoints.
    Returns (healed_vertices, actions).
    """
    if len(vertices) < 2:
        return vertices, []

    actions = []
    healed = list(vertices)
    
    # If first and last are close but not identical, snap them together
    if len(healed) > 2:
        if distance_3d(healed[0], healed[-1]) <= tolerance:
            healed[-1] = healed[0]
            actions.append("closed_endpoint_gap")
    
    return healed, actions


def deduplicate_vertices(
    vertices: List[Vector3], tolerance: float
) -> Tuple[List[Vector3], List[str]]:
    """
    Remove consecutive duplicate vertices within tolerance.
    Returns (deduplicated_vertices, actions).
    """
    if len(vertices) < 2:
        return vertices, []

    actions = []
    result = [vertices[0]]
    removed_count = 0

    for i in range(1, len(vertices)):
        if not vector_equal(vertices[i], result[-1], tolerance):
            result.append(vertices[i])
        else:
            removed_count += 1

    if removed_count > 0:
        actions.append(f"deduped_{removed_count}_vertices")
    
    return result, actions


def heal_polyline_geometry(
    geometry: Dict[str, Any], tolerance: float, snap_to_grid: bool = False, grid_size: float = 0.001
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Apply healing operations to a polyline geometry payload.
    Returns (healed_geometry, action_descriptions).
    """
    actions = []
    healed_geo = dict(geometry)
    vertices = healed_geo.get("vertices", [])
    if not vertices:
        return healed_geo, actions

    # Convert to Vector3 if raw dicts
    verts = [
        v if isinstance(v, Vector3) else Vector3(**v) 
        for v in vertices
    ]

    # Deduplicate consecutive vertices
    verts, dedup_actions = deduplicate_vertices(verts, tolerance)
    actions.extend(dedup_actions)

    # Close gaps at endpoints
    verts, gap_actions = close_gaps_in_polyline(verts, tolerance)
    actions.extend(gap_actions)

    # Normalize winding for closed polygons
    if healed_geo.get("closed", False):
        verts = normalize_polygon_winding(verts)
        actions.append("normalized_winding")

    # Snap to grid if requested
    if snap_to_grid and grid_size > 0:
        snapped = []
        for v in verts:
            snapped_v = Vector3(
                x=round(v.x / grid_size) * grid_size,
                y=round(v.y / grid_size) * grid_size,
                z=round(v.z / grid_size) * grid_size,
            )
            snapped.append(snapped_v)
        verts = snapped
        actions.append("snapped_to_grid")

    healed_geo["vertices"] = [v.model_dump() for v in verts]
    return healed_geo, actions


def heal_entity(
    entity: Entity,
    tolerance: float,
    snap_to_grid: bool = False,
    grid_size: float = 0.001,
) -> Tuple[Entity, List[str]]:
    """
    Apply healing operations to an entity.
    Returns (healed_entity, action_descriptions).
    """
    actions = []
    healed = entity.model_copy(deep=True)

    if entity.type in (EntityType.POLYLINE, EntityType.POLYGON):
        healed.geometry, geo_actions = heal_polyline_geometry(
            healed.geometry, tolerance, snap_to_grid, grid_size
        )
        actions.extend(geo_actions)

    return healed, actions


def heal_entities(
    entities: List[Entity],
    tolerance: float,
    snap_to_grid: bool = False,
    grid_size: float = 0.001,
) -> Tuple[List[Entity], List[HealingAction]]:
    """
    Apply healing to all entities and return healed entities with action records.
    Returns (healed_entities, healing_actions).
    """
    healed_entities = []
    healing_actions = []

    for entity in entities:
        healed, actions = heal_entity(entity, tolerance, snap_to_grid, grid_size)
        healed_entities.append(healed)

        if actions:
            action = HealingAction(
                kind=HealingActionKind.VERTEX_DEDUP,
                affected_entities=[entity.id],
                description="; ".join(actions),
                severity="info",
            )
            healing_actions.append(action)

    return healed_entities, healing_actions


def detect_duplicate_entities(
    entities: List[Entity], tolerance: float
) -> List[Tuple[str, str]]:
    """
    Find pairs of entities that are duplicate (same geometry within tolerance).
    Returns list of (entity_id1, entity_id2) pairs.
    """
    duplicates = []
    seen = set()

    for i, e1 in enumerate(entities):
        if e1.id in seen:
            continue
        for e2 in entities[i + 1 :]:
            if e2.id in seen:
                continue
            if e1.type != e2.type:
                continue
            if e1.layer != e2.layer:
                continue
            
            # Simple check: compare bboxes within tolerance
            if (
                distance_3d(e1.bbox.min, e2.bbox.min) <= tolerance
                and distance_3d(e1.bbox.max, e2.bbox.max) <= tolerance
            ):
                duplicates.append((e1.id, e2.id))
                seen.add(e2.id)
                break

    return duplicates


def remove_duplicate_entities(
    entities: List[Entity], tolerance: float
) -> Tuple[List[Entity], List[HealingAction]]:
    """
    Remove duplicate entities and return results with action records.
    Returns (deduplicated_entities, healing_actions).
    """
    duplicates = detect_duplicate_entities(entities, tolerance)
    if not duplicates:
        return entities, []

    # Build set of IDs to remove (keep first of each pair)
    to_remove = set()
    for id1, id2 in duplicates:
        to_remove.add(id2)

    result = [e for e in entities if e.id not in to_remove]
    action = HealingAction(
        kind=HealingActionKind.DUPLICATE_REMOVE,
        affected_entities=list(to_remove),
        description=f"Removed {len(to_remove)} duplicate entities",
        severity="info",
    )

    return result, [action] if to_remove else []


def validate_healed_geometry(
    original: Entity, healed: Entity, tolerance: float
) -> bool:
    """
    Validate that healed geometry hasn't diverged too much from original.
    For now, check bbox didn't grow by more than tolerance.
    """
    if original.type not in (EntityType.POLYLINE, EntityType.POLYGON):
        return True

    # Simple check: bboxes should be similar
    bbox_growth = distance_3d(
        original.bbox.max, healed.bbox.max
    ) + distance_3d(original.bbox.min, healed.bbox.min)
    
    return bbox_growth <= tolerance * 10


def heal_topology(
    entities: List[Entity],
    tolerance: float,
    snap_to_grid: bool = False,
    grid_size: float = 0.001,
) -> Tuple[List[Entity], List[HealingAction]]:
    """
    Apply full topology healing pipeline.
    Returns (healed_entities, all_healing_actions).
    """
    all_actions = []

    # Step 1: Heal individual entity geometries
    healed, geo_actions = heal_entities(entities, tolerance, snap_to_grid, grid_size)
    all_actions.extend(geo_actions)

    # Step 2: Remove duplicates
    healed, dup_actions = remove_duplicate_entities(healed, tolerance)
    all_actions.extend(dup_actions)

    # Step 3: Validate
    for orig, new in zip(entities, healed):
        if not validate_healed_geometry(orig, new, tolerance):
            action = HealingAction(
                kind=HealingActionKind.VERTEX_DEDUP,
                affected_entities=[orig.id],
                description=f"Geometry divergence detected but accepted",
                severity="warning",
            )
            all_actions.append(action)

    return healed, all_actions
