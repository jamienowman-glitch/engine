"""
BoQ Quantities Service - Generate bill of quantities from semantic models.

Implements:
- Element-to-BoQItem conversion with quantity formulas
- Scope tagging and aggregation
- Service with caching by semantics_id + calc_version
- Artifact registration
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from engines.cad_semantics.models import SemanticModel
from engines.boq_quantities.formulas import calculate_quantity, deterministic_boq_item_id
from engines.boq_quantities.models import BoQItem, BoQModel, BoQResponse, Scope


class BoQCache:
    """In-memory cache for BoQ models."""
    
    def __init__(self, max_entries: int = 50):
        self.cache: Dict[str, BoQModel] = {}
        self.max_entries = max_entries
    
    def cache_key(self, semantic_model_id: str, calc_version: str, params_hash: str) -> str:
        """Generate cache key."""
        return f"{semantic_model_id}:{calc_version}:{params_hash}"
    
    def get(self, key: str) -> Optional[BoQModel]:
        """Retrieve cached model."""
        return self.cache.get(key)
    
    def put(self, key: str, model: BoQModel) -> None:
        """Store model in cache."""
        if len(self.cache) >= self.max_entries:
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = model
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()


class BoQQuantitiesService:
    """Generate bill of quantities from semantic models."""
    
    def __init__(self):
        self.cache = BoQCache()
    
    def _params_hash(self, params: Dict[str, Any]) -> str:
        """Hash calculation parameters."""
        if not params:
            return "default"
        items = sorted(params.items())
        key = str(items)
        return hashlib.sha256(key.encode()).hexdigest()[:8]
    
    def quantify(
        self,
        semantic_model: SemanticModel,
        calc_version: str = "1.0.0",
        calc_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[BoQModel, BoQResponse]:
        """
        Generate BoQ from semantic model.
        
        Args:
            semantic_model: Classified CAD semantics
            calc_version: Version of BoQ calculation rules
            calc_params: Thicknesses, heights, tolerances
        
        Returns:
            (BoQModel, BoQResponse)
        """
        params = calc_params or {}
        
        # Check cache
        cache_key = self.cache.cache_key(
            semantic_model.id,
            calc_version,
            self._params_hash(params),
        )
        cached = self.cache.get(cache_key)
        if cached:
            response = self._model_to_response(cached)
            return cached, response
        
        # Initialize BoQ model
        boq_model = BoQModel(
            semantic_model_id=semantic_model.id,
            calc_version=calc_version,
            calc_params=params,
        )
        
        # Calculate quantities for each element
        items_by_scope: Dict[str, List[BoQItem]] = {}
        
        for element in semantic_model.elements:
            try:
                quantity, unit, formula, meta = calculate_quantity(
                    element,
                    semantic_model,
                    params,
                )
                
                # Create BoQ item
                item = BoQItem(
                    id=deterministic_boq_item_id(element.id, element.semantic_type.value),
                    element_type=element.semantic_type.value,
                    quantity=round(quantity, 3),
                    unit=unit,
                    level_id=element.level_id,
                    scope_id=element.level_id,  # Use level as scope
                    source_element_ids=[element.id],
                    source_cad_entity_ids=[element.cad_entity_id],
                    formula_used=formula,
                    calc_version=calc_version,
                    meta=meta,
                )
                
                boq_model.items.append(item)
                
                # Track by scope
                scope_key = element.level_id or "default"
                if scope_key not in items_by_scope:
                    items_by_scope[scope_key] = []
                items_by_scope[scope_key].append(item)
                
            except Exception as e:
                # Log warning but continue
                boq_model.meta.setdefault("warnings", []).append(
                    f"Failed to quantify {element.id}: {str(e)}"
                )
        
        # Sort items deterministically
        boq_model.items.sort(key=lambda x: (x.element_type, x.id))
        
        # Create scopes
        for level in semantic_model.levels:
            scope = Scope(
                scope_name=level.name,
                level_id=level.id,
                item_count=len(items_by_scope.get(level.id, [])),
            )
            
            # Calculate scope totals
            scope_items = items_by_scope.get(level.id, [])
            for item in scope_items:
                if item.unit.value.endswith("²"):  # Area
                    scope.total_area = (scope.total_area or 0) + item.quantity
                elif item.unit.value.endswith("³"):  # Volume
                    scope.total_volume = (scope.total_volume or 0) + item.quantity
                elif item.unit in ("m", "mm", "cm", "ft", "in"):  # Length
                    scope.total_length = (scope.total_length or 0) + item.quantity
                elif item.unit in ("count", "no"):  # Count
                    scope.total_count += 1
            
            boq_model.scopes.append(scope)
        
        # Count items by type
        type_counts: Dict[str, int] = {}
        for item in boq_model.items:
            key = item.element_type
            type_counts[key] = type_counts.get(key, 0) + 1
        
        boq_model.item_count = len(boq_model.items)
        boq_model.item_count_by_type = type_counts
        
        # Compute model hash
        item_hashes = [hashlib.sha256(item.id.encode()).hexdigest() for item in boq_model.items]
        hash_str = "".join(item_hashes) + calc_version
        boq_model.model_hash = hashlib.sha256(hash_str.encode()).hexdigest()[:16]
        
        # Cache
        self.cache.put(cache_key, boq_model)
        
        # Build response
        response = self._model_to_response(boq_model)
        
        return boq_model, response
    
    def _model_to_response(self, model: BoQModel) -> BoQResponse:
        """Convert BoQModel to response."""
        return BoQResponse(
            boq_artifact_id="",  # Set by caller
            boq_model_id=model.id,
            item_count=model.item_count,
            item_count_by_type=model.item_count_by_type,
            scope_count=len(model.scopes),
            model_hash=model.model_hash or "",
            calc_version=model.calc_version,
            created_at=model.created_at,
            meta={
                "warnings": model.meta.get("warnings", []),
                "scope_names": [s.scope_name for s in model.scopes],
            },
        )
    
    def register_artifact(
        self,
        semantic_model_id: str,
        boq_model: BoQModel,
        calc_version: str = "1.0.0",
        context: Optional[Any] = None,
    ) -> str:
        """
        Register BoQ artifact in media_v2.
        
        Returns artifact ID for registered BoQ model.
        """
        # Generate deterministic artifact ID
        artifact_id = f"boq_{semantic_model_id}_{boq_model.model_hash}"
        
        # TODO: Register with media_v2 infrastructure
        return artifact_id


# Module-level default service
_default_service: Optional[BoQQuantitiesService] = None


def get_boq_service() -> BoQQuantitiesService:
    """Get default BoQ service."""
    global _default_service
    if _default_service is None:
        _default_service = BoQQuantitiesService()
    return _default_service


def set_boq_service(service: BoQQuantitiesService) -> None:
    """Override default service (for testing)."""
    global _default_service
    _default_service = service
