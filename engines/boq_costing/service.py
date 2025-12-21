"""
BoQ Costing Service - Generate costs from BoQ using rate catalogs.

Implements:
- BoQ item pricing
- Catalog application with versioning
- Currency conversion
- Service with caching by boq_id + catalog_version + currency
- Artifact registration
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from engines.boq_quantities.models import BoQModel, BoQItem
from engines.boq_costing.catalog import apply_markup_and_tax, create_default_catalog
from engines.boq_costing.models import (
    Currency,
    CostAssumption,
    CostCatalog,
    CostItem,
    CostModel,
    CostResponse,
    CostRollup,
)


class CostCache:
    """In-memory cache for cost models."""
    
    def __init__(self, max_entries: int = 50):
        self.cache: Dict[str, CostModel] = {}
        self.max_entries = max_entries
    
    def cache_key(
        self,
        boq_model_id: str,
        catalog_version: str,
        currency: str,
        params_hash: str,
    ) -> str:
        """Generate cache key."""
        return f"{boq_model_id}:{catalog_version}:{currency}:{params_hash}"
    
    def get(self, key: str) -> Optional[CostModel]:
        """Retrieve cached model."""
        return self.cache.get(key)
    
    def put(self, key: str, model: CostModel) -> None:
        """Store model in cache."""
        if len(self.cache) >= self.max_entries:
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = model
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()


class BoQCostingService:
    """Generate cost estimates from BoQ models."""
    
    def __init__(self):
        self.cache = CostCache()
        self.default_catalog = create_default_catalog()
    
    def _params_hash(self, params: Dict[str, Any]) -> str:
        """Hash cost parameters."""
        if not params:
            return "default"
        items = sorted(params.items())
        key = str(items)
        return hashlib.sha256(key.encode()).hexdigest()[:8]
    
    def estimate_cost(
        self,
        boq_model: BoQModel,
        catalog: Optional[CostCatalog] = None,
        currency: Currency = Currency.USD,
        markup_pct: float = 0.0,
        tax_pct: float = 0.0,
        catalog_overrides: Optional[Dict[str, float]] = None,
    ) -> Tuple[CostModel, CostResponse]:
        """
        Generate cost estimate from BoQ.
        
        Args:
            boq_model: Bill of quantities to price
            catalog: Cost catalog (uses default if None)
            currency: Target currency for costs
            markup_pct: Markup percentage to apply
            tax_pct: Tax percentage to apply
            catalog_overrides: Override specific rates
        
        Returns:
            (CostModel, CostResponse)
        """
        # Use default catalog if not provided
        if catalog is None:
            catalog = self.default_catalog
        
        # Check cache
        params = {
            "markup": markup_pct,
            "tax": tax_pct,
            "overrides": len(catalog_overrides or {})
        }
        cache_key = self.cache.cache_key(
            boq_model.id,
            catalog.version,
            currency.value,
            self._params_hash(params),
        )
        cached = self.cache.get(cache_key)
        if cached:
            response = self._model_to_response(cached)
            return cached, response
        
        # Initialize cost model
        cost_model = CostModel(
            boq_model_id=boq_model.id,
            currency=currency,
            catalog_version=catalog.version,
            markup_pct=markup_pct,
            tax_pct=tax_pct,
        )
        
        # Price each BoQ item
        items_by_scope: Dict[str, List[CostItem]] = {}
        total_cost = 0.0
        
        for boq_item in boq_model.items:
            # Get rate from catalog
            unit_rate = catalog.get_rate(
                boq_item.element_type,
                boq_item.unit.value,
                fallback=None,
            )
            
            # Handle missing rate
            if unit_rate is None:
                if catalog_overrides and boq_item.element_type in catalog_overrides:
                    unit_rate = catalog_overrides[boq_item.element_type]
                else:
                    # Flag warning but use 0
                    unit_rate = 0.0
                    cost_model.meta.setdefault("warnings", []).append(
                        f"No rate for {boq_item.element_type}/{boq_item.unit.value}"
                    )
            
            # Calculate extended cost
            extended_cost = boq_item.quantity * unit_rate
            
            # Apply currency conversion if needed
            extended_cost_base = extended_cost
            if catalog.currency != currency:
                extended_cost = catalog.convert_currency(
                    extended_cost,
                    catalog.currency,
                    currency,
                )
            
            # Create cost item
            assumptions = []
            if markup_pct > 0:
                assumptions.append(
                    CostAssumption(key="markup", value=markup_pct, applied=True)
                )
            if tax_pct > 0:
                assumptions.append(
                    CostAssumption(key="tax", value=tax_pct, applied=True)
                )
            
            cost_item = CostItem(
                id=f"cost_{boq_item.id}",
                boq_item_id=boq_item.id,
                boq_item_type=boq_item.element_type,
                boq_item_quantity=boq_item.quantity,
                boq_item_unit=boq_item.unit.value,
                unit_rate=unit_rate,
                currency=currency,
                extended_cost=round(extended_cost, 2),
                extended_cost_in_base_currency=round(extended_cost_base, 2),
                assumptions=assumptions,
                source_catalog_version=catalog.version,
                meta={
                    "boq_unit": boq_item.unit.value,
                    "quantity": boq_item.quantity,
                },
            )
            
            cost_model.items.append(cost_item)
            total_cost += extended_cost
            
            # Track by scope
            scope_key = boq_item.scope_id or "default"
            if scope_key not in items_by_scope:
                items_by_scope[scope_key] = []
            items_by_scope[scope_key].append(cost_item)
        
        # Sort items deterministically
        cost_model.items.sort(key=lambda x: (x.boq_item_type, x.id))
        
        # Apply markup and tax
        if markup_pct > 0 or tax_pct > 0:
            marked_up, tax_amount, with_tax = apply_markup_and_tax(
                total_cost,
                markup_pct,
                tax_pct,
            )
            total_cost = with_tax
            cost_model.meta["markup_amount"] = round(marked_up - total_cost / (1 + tax_pct / 100) if tax_pct else marked_up - total_cost, 2)
            cost_model.meta["tax_amount"] = round(tax_amount, 2)
        
        cost_model.total_cost = round(total_cost, 2)
        cost_model.total_cost_by_currency[currency.value] = round(total_cost, 2)
        
        # Create rollups per scope
        for scope_key, scope_items in items_by_scope.items():
            scope_total = sum(item.extended_cost for item in scope_items)
            
            # Breakdown by type
            by_type: Dict[str, float] = {}
            for item in scope_items:
                by_type[item.boq_item_type] = by_type.get(item.boq_item_type, 0) + item.extended_cost
            
            rollup = CostRollup(
                scope_id=scope_key,
                scope_name=scope_key,
                item_count=len(scope_items),
                total_cost=round(scope_total, 2),
                currency=currency,
                by_type=by_type,
            )
            cost_model.rollups.append(rollup)
        
        # Compute model hash
        item_hashes = [hashlib.sha256(item.id.encode()).hexdigest() for item in cost_model.items]
        hash_str = "".join(item_hashes) + catalog.version + currency.value
        cost_model.model_hash = hashlib.sha256(hash_str.encode()).hexdigest()[:16]
        
        # Cache
        self.cache.put(cache_key, cost_model)
        
        # Build response
        response = self._model_to_response(cost_model)
        
        return cost_model, response
    
    def _model_to_response(self, model: CostModel) -> CostResponse:
        """Convert CostModel to response."""
        return CostResponse(
            cost_artifact_id="",  # Set by caller
            cost_model_id=model.id,
            total_cost=model.total_cost,
            currency=model.currency,
            item_count=len(model.items),
            rollup_count=len(model.rollups),
            catalog_version=model.catalog_version,
            model_hash=model.model_hash or "",
            created_at=model.created_at,
            meta={
                "warnings": model.meta.get("warnings", []),
                "markup_pct": model.markup_pct,
                "tax_pct": model.tax_pct,
            },
        )
    
    def register_artifact(
        self,
        boq_model_id: str,
        cost_model: CostModel,
        catalog_version: str = "1.0.0",
        context: Optional[Any] = None,
    ) -> str:
        """
        Register cost artifact in media_v2.
        
        Returns artifact ID for registered cost model.
        """
        # Generate deterministic artifact ID
        artifact_id = f"cost_{boq_model_id}_{cost_model.model_hash}"
        
        # TODO: Register with media_v2 infrastructure
        return artifact_id


# Module-level default service
_default_service: Optional[BoQCostingService] = None


def get_costing_service() -> BoQCostingService:
    """Get default costing service."""
    global _default_service
    if _default_service is None:
        _default_service = BoQCostingService()
    return _default_service


def set_costing_service(service: BoQCostingService) -> None:
    """Override default service (for testing)."""
    global _default_service
    _default_service = service
