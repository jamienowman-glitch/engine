"""
Semantic Classification Rules - Heuristics and patterns for element type detection.

Implements:
- Layer name pattern matching
- Geometry-based hints (aspect ratio, closed polylines)
- Elevation/level inference
- Confidence scoring
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from engines.cad_ingest.models import Entity, EntityType
from engines.cad_semantics.models import SemanticType


class ClassificationRule:
    """Base rule for element classification."""
    
    def __init__(self, name: str, patterns: List[str], semantic_type: SemanticType):
        self.name = name
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.semantic_type = semantic_type
    
    def matches_layer(self, layer_name: str) -> bool:
        """Check if layer name matches rule patterns."""
        return any(p.search(layer_name) for p in self.patterns)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Geometry-based matching (override in subclasses)."""
        return True


class WallRule(ClassificationRule):
    """Classify walls by layer name and geometry."""
    
    def __init__(self):
        patterns = [
            r"wall.*",
            r".*wall",
            r"w\d+",
            r"elevation.*",
            r"structural.*",
        ]
        super().__init__("WallRule", patterns, SemanticType.WALL)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Walls are typically polylines or solids."""
        return entity.type in (EntityType.POLYLINE, EntityType.SOLID, EntityType.POLYGON)


class DoorRule(ClassificationRule):
    """Classify doors by layer name and geometry."""
    
    def __init__(self):
        patterns = [
            r"door.*",
            r".*door",
            r"d\d+",
            r"opening.*",
        ]
        super().__init__("DoorRule", patterns, SemanticType.DOOR)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Doors are typically small shapes."""
        return entity.type in (EntityType.CIRCLE, EntityType.POLYLINE)


class WindowRule(ClassificationRule):
    """Classify windows by layer name and geometry."""
    
    def __init__(self):
        patterns = [
            r"window.*",
            r".*window",
            r"w[0-9]+",
            r"fenestration.*",
        ]
        super().__init__("WindowRule", patterns, SemanticType.WINDOW)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Windows are typically circles or small polylines."""
        return entity.type in (EntityType.CIRCLE, EntityType.POLYLINE)


class SlabRule(ClassificationRule):
    """Classify slabs by layer name and geometry."""
    
    def __init__(self):
        patterns = [
            r"slab.*",
            r".*slab",
            r"floor.*",
            r".*floor",
            r"deck.*",
            r"roof.*",
        ]
        super().__init__("SlabRule", patterns, SemanticType.SLAB)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Slabs are typically large closed polygons."""
        return entity.type in (EntityType.SOLID, EntityType.POLYGON)


class ColumnRule(ClassificationRule):
    """Classify columns by layer name and geometry."""
    
    def __init__(self):
        patterns = [
            r"column.*",
            r".*column",
            r"pillar.*",
            r"c\d+",
            r"support.*",
        ]
        super().__init__("ColumnRule", patterns, SemanticType.COLUMN)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Columns are typically circles or small solids."""
        return entity.type in (EntityType.CIRCLE, EntityType.SOLID)


class StairRule(ClassificationRule):
    """Classify stairs by layer name."""
    
    def __init__(self):
        patterns = [
            r"stair.*",
            r".*stair",
            r"ramp.*",
        ]
        super().__init__("StairRule", patterns, SemanticType.STAIR)


class RoomRule(ClassificationRule):
    """Classify rooms by layer name and geometry."""
    
    def __init__(self):
        patterns = [
            r"room.*",
            r".*room",
            r"space.*",
            r"area.*",
        ]
        super().__init__("RoomRule", patterns, SemanticType.ROOM)
    
    def matches_geometry(self, entity: Entity) -> bool:
        """Rooms are closed polygons."""
        return entity.type in (EntityType.POLYGON, EntityType.SOLID)


class LevelRule(ClassificationRule):
    """Classify levels by layer name."""
    
    def __init__(self):
        patterns = [
            r"level.*",
            r".*level",
            r"story.*",
            r"floor.*",
            r"l\d+",
        ]
        super().__init__("LevelRule", patterns, SemanticType.LEVEL)


class ClassificationRuleSet:
    """Collection of classification rules with priority."""
    
    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        self.rules = [
            WallRule(),
            SlabRule(),
            ColumnRule(),
            DoorRule(),
            WindowRule(),
            StairRule(),
            RoomRule(),
            LevelRule(),
        ]
        self.overrides = overrides or {}
    
    def classify(self, entity: Entity, layer_name: str) -> Tuple[SemanticType, List[str], float]:
        """
        Classify an entity and return (type, rule_hits, confidence).
        Returns (SemanticType.UNKNOWN, [], 0.0) if no rules match.
        """
        # Check for override
        override_key = f"{entity.id}:{layer_name}"
        if override_key in self.overrides:
            return self.overrides[override_key], ["override"], 1.0
        
        hits = []
        
        # Try each rule in priority order
        for rule in self.rules:
            if rule.matches_layer(layer_name) and rule.matches_geometry(entity):
                hits.append(rule.name)
                confidence = 1.0 if len(hits) == 1 else 0.8  # Lower conf for multi-rule matches
                return rule.semantic_type, hits, confidence
        
        # No match
        return SemanticType.UNKNOWN, [], 0.0


def infer_levels_from_elevations(entities: List[Entity]) -> Tuple[Dict[float, str], Optional[str]]:
    """
    Infer building levels from Z-coordinates using clustering.
    Returns (level_map, warning_message).
    level_map maps elevation (z) to level_id.
    """
    elevations = []
    for entity in entities:
        z = entity.bbox.min.z
        if z is not None:
            elevations.append(z)
    
    if not elevations:
        # Fallback with warning
        return {0.0: "L0"}, "No entity elevations found; defaulting to L0 at 0.0"
    
    # Simple clustering: group similar Z values
    elevations = sorted(set(elevations))
    levels = {}
    tolerance = 0.1  # Tolerance for same level
    
    current_level = None
    level_count = 0
    
    for z in elevations:
        if current_level is None or z - current_level > tolerance:
            current_level = z
            level_id = f"L{level_count}"
            levels[z] = level_id
            level_count += 1
        else:
            # Use existing level
            levels[z] = f"L{level_count - 1}"
    
    return levels, None


def deterministic_semantic_id(entity_id: str, semantic_type: SemanticType) -> str:
    """Generate deterministic ID for semantic element."""
    combined = f"{entity_id}:{semantic_type.value}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
