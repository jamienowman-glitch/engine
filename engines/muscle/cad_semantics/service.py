"""
CAD Semantics Service - Orchestrate classification, level detection, and graph building.

Implements:
- Element classification against ruleset
- Level inference
- Spatial graph construction
- Caching by cad_model_id + rule_version
- Artifact registration
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from engines.cad_ingest.models import CadModel
from engines.cad_semantics.graph import build_spatial_graph
from engines.cad_semantics.models import (
    Level,
    SemanticElement,
    SemanticModel,
    SemanticResponse,
    SemanticType,
)
from engines.cad_semantics.rules import (
    ClassificationRuleSet,
    deterministic_semantic_id,
    infer_levels_from_elevations,
)


class SemanticCache:
    """In-memory cache for semantic models."""
    
    def __init__(self, max_entries: int = 50):
        self.cache: Dict[str, SemanticModel] = {}
        self.max_entries = max_entries
    
    def cache_key(self, cad_model_id: str, rule_version: str, overrides_hash: str) -> str:
        """Generate cache key."""
        return f"{cad_model_id}:{rule_version}:{overrides_hash}"
    
    def get(self, key: str) -> Optional[SemanticModel]:
        """Retrieve cached model."""
        return self.cache.get(key)
    
    def put(self, key: str, model: SemanticModel) -> None:
        """Store model in cache."""
        if len(self.cache) >= self.max_entries:
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = model
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()


class SemanticClassificationService:
    """Classify CAD model and build semantics."""
    
    def __init__(self):
        self.cache = SemanticCache()
    
    def _overrides_hash(self, overrides: Dict[str, Any]) -> str:
        """Hash rule overrides."""
        if not overrides:
            return "none"
        items = sorted(overrides.items())
        key = str(items)
        return hashlib.sha256(key.encode()).hexdigest()[:8]
    
    def semanticize(
        self,
        cad_model: Optional[CadModel] = None,
        rule_version: str = "1.0.0",
        rule_overrides: Optional[Dict[str, Any]] = None,
        cad_model_id: Optional[str] = None,
    ) -> Tuple[SemanticModel, SemanticResponse]:
        """
        Classify CAD model and build semantic model.
        
        Args:
            cad_model: Ingested and healed CAD model (or None if cad_model_id provided)
            rule_version: Version of rules to apply
            rule_overrides: Per-element type overrides
            cad_model_id: Optional CAD model ID; if provided alone, will not actually load
        
        Returns:
            (SemanticModel, SemanticResponse)
        """
        if cad_model is None and cad_model_id is None:
            raise ValueError("Either cad_model or cad_model_id must be provided")
        
        # For API usage: cad_model_id without cad_model is a valid contract,
        # but we'll require cad_model for actual execution
        if cad_model is None:
            raise ValueError("In current implementation, cad_model object is required")

        overrides = rule_overrides or {}
        
        # Check cache
        cache_key = self.cache.cache_key(cad_model.id, rule_version, self._overrides_hash(overrides))
        cached = self.cache.get(cache_key)
        if cached:
            response = self._model_to_response(cached)
            return cached, response
        
        # Initialize semantic model
        semantic_model = SemanticModel(
            cad_model_id=cad_model.id,
            rule_version=rule_version,
            rule_overrides=overrides,
        )
        
        # Initialize rule set
        ruleset = ClassificationRuleSet(overrides=overrides)
        
        # Classify each entity
        for entity in cad_model.entities:
            semantic_type, rule_hits, confidence = ruleset.classify(entity, entity.layer)
            
            # Create semantic element
            sem_elem = SemanticElement(
                id=deterministic_semantic_id(entity.id, semantic_type),
                cad_entity_id=entity.id,
                semantic_type=semantic_type,
                layer=entity.layer,
                geometry_ref=entity.geometry,
                rule_version=rule_version,
                confidence=confidence,
                rule_hits=rule_hits,
            )
            
            semantic_model.elements.append(sem_elem)
        
        # Infer levels from elevations
        level_map, level_warning = infer_levels_from_elevations(cad_model.entities)
        
        if level_warning:
            semantic_model.warnings.append(level_warning)
        
        # Attach level_ids to elements and create Level objects
        created_levels = set()
        level_objects = []
        
        for elem in semantic_model.elements:
            z = 0.0
            if elem.geometry_ref:
                z = elem.geometry_ref.get("z", 0.0)
            
            # Find closest level
            closest_level_id = min(level_map.items(), key=lambda x: abs(x[0] - z))[1]
            elem.level_id = closest_level_id
            elem.elevation = z
            
            # Create Level object if not yet created
            if closest_level_id not in created_levels:
                level = Level(
                    id=closest_level_id,
                    name=closest_level_id,
                    elevation=z,
                    index=int(closest_level_id[1:]),
                )
                level_objects.append(level)
                created_levels.add(closest_level_id)
        
        semantic_model.levels = level_objects
        semantic_model.level_count = len(level_objects)
        
        # Count elements by type
        type_counts: Dict[str, int] = {}
        for elem in semantic_model.elements:
            key = elem.semantic_type.value
            type_counts[key] = type_counts.get(key, 0) + 1
        
        semantic_model.element_count_by_type = type_counts
        
        # Build spatial graph
        semantic_model.spatial_graph = build_spatial_graph(semantic_model.elements)
        
        # Compute model hash
        model_repr = f"{len(semantic_model.elements)}:{semantic_model.spatial_graph.graph_hash}:{rule_version}"
        semantic_model.model_hash = hashlib.sha256(model_repr.encode()).hexdigest()[:16]
        
        # Cache
        self.cache.put(cache_key, semantic_model)
        
        # Build response
        response = self._model_to_response(semantic_model)
        
        return semantic_model, response
    
    def _model_to_response(self, model: SemanticModel) -> SemanticResponse:
        """Convert SemanticModel to response."""
        counts = model.element_count_by_type
        
        return SemanticResponse(
            semantic_artifact_id="",  # Set by caller
            semantic_model_id=model.id,
            element_count=len(model.elements),
            level_count=model.level_count,
            wall_count=counts.get("wall", 0),
            door_count=counts.get("door", 0),
            window_count=counts.get("window", 0),
            slab_count=counts.get("slab", 0),
            column_count=counts.get("column", 0),
            unknown_count=counts.get("unknown", 0),
            graph_edge_count=len(model.spatial_graph.edges),
            room_count=counts.get("room", 0),
            stair_count=counts.get("stair", 0),
            rule_version=model.rule_version,
            created_at=model.created_at,
            meta={
                "model_hash": model.model_hash,
                "graph_hash": model.spatial_graph.graph_hash,
                "adjacency_edges": model.spatial_graph.adjacency_edge_count,
                "containment_edges": model.spatial_graph.containment_edge_count,
                "connectivity_edges": model.spatial_graph.connectivity_edge_count,
                "level_summary": {lvl.id: lvl.elevation for lvl in model.levels},
                "warnings": model.warnings,
            },
        )
    
    def register_artifact(
        self,
        cad_model_id: str,
        semantic_model: SemanticModel,
        rule_version: str = "1.0.0",
        context: Optional[Any] = None,
    ) -> str:
        """
        Register semantic artifact in media_v2.
        
        Returns artifact ID for registered semantic model.
        """
        # Generate deterministic artifact ID
        artifact_id = f"sem_{cad_model_id}_{semantic_model.model_hash}"
        
        # Prepare metadata strictly required by media_v2
        meta = {
            "model_hash": semantic_model.model_hash,
            "graph_hash": semantic_model.spatial_graph.graph_hash,
            "rule_version": semantic_model.rule_version,
            "element_count": len(semantic_model.elements),
            "level_count": semantic_model.level_count,
            # "warnings": semantic_model.warnings  # Optional but good
        }
        
        # Validation check (runtime safety)
        # In a real implementation this would happen inside the media service call,
        # but we check it here to fail fast if our service logic drifts from the schema.
        from engines.media_v2.models import DerivedArtifact
        
        # Mock context for validation check
        DerivedArtifact(
            id=artifact_id,
            parent_asset_id=cad_model_id,
            tenant_id="validate_tenant", # Placeholder if context not provided
            env="validate_env",
            kind="cad_semantics",
            uri=f"s3://bucket/{artifact_id}.json",
            meta=meta
        )
        
        # TODO: Register with media_v2 infrastructure
        # For now, just return the ID
        return artifact_id
    
    def get_artifact(self, semantic_artifact_id: str) -> SemanticResponse:
        """
        Retrieve a registered semantic artifact.
        
        TODO: Implement actual retrieval from media_v2.
        """
        raise NotImplementedError("Artifact retrieval not yet implemented")



# Module-level default service
_default_service: Optional[SemanticClassificationService] = None


def get_semantic_service() -> SemanticClassificationService:
    """Get default semantic service."""
    global _default_service
    if _default_service is None:
        _default_service = SemanticClassificationService()
    return _default_service


def set_semantic_service(service: SemanticClassificationService) -> None:
    """Override default service (for testing)."""
    global _default_service
    _default_service = service
