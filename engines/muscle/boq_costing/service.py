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
from engines.boq_costing.catalog import (
    apply_markup_and_tax, 
    create_default_catalog, 
    get_catalog_registry
)
from engines.boq_costing.models import (
    Currency,
    CostAssumption,
    CostCatalog,
    CostItem,
    CostModel,
    CostRequest,
    CostResponse,
    CostRollup,
)
from engines.boq_costing.catalog import (
    apply_markup_and_tax, 
    create_default_catalog, 
    get_catalog_registry
)
from engines.boq_costing.models import (
    Currency,
    CostAssumption,
    CostCatalog,
    CostItem,
    CostModel,
    CostRequest,
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
        catalog: Optional[CostCatalog] = None, # Deprecated in favor of version string in logic
        currency: Currency = Currency.USD,
        markup_pct: float = 0.0,
        tax_pct: float = 0.0,
        catalog_overrides: Optional[Dict[str, float]] = None,
        # Helper to support new request-style
        catalog_version: str = "1.0.0",
    ) -> Tuple[CostModel, CostResponse]:
        """
        Generate cost estimate from BoQ.
        
        Args:
            boq_model: Bill of quantities to price
            catalog: (Deprecated) Cost catalog object
            currency: Target currency for costs
            markup_pct: Markup percentage to apply
            tax_pct: Tax percentage to apply
            catalog_overrides: Override specific rates
            catalog_version: Version of catalog to use
        
        Returns:
            (CostModel, CostResponse)
        """
        # Resolve catalog
        if catalog is None:
            registry = get_catalog_registry()
            catalog = registry.get(catalog_version)
            if not catalog:
                if catalog_version == "1.0.0":
                    catalog = self.default_catalog
                else:
                    raise ValueError(f"Catalog version '{catalog_version}' not found")
        
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
            # Get base rate (Catalog -> Override)
            unit_rate = catalog.get_rate(
                boq_item.element_type,
                boq_item.unit.value,
                fallback=None,
            )
            
            # Apply Request Override if present
            if catalog_overrides and boq_item.element_type in catalog_overrides:
                unit_rate = catalog_overrides[boq_item.element_type]
            
            # Handling missing rate
            if unit_rate is None:
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
            
            # Deterministic ID based on boq item id
            item_hash = hashlib.sha256(f"cost_{boq_item.id}".encode()).hexdigest()[:16]
            
            cost_item = CostItem(
                id=item_hash,
                boq_item_id=boq_item.id,
                boq_item_type=boq_item.element_type,
                boq_item_quantity=boq_item.quantity,
                boq_item_unit=boq_item.unit.value,
                unit_rate=unit_rate, # Storing used rate (might be varying currency if mixed)
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
        
        # Apply global markup and tax to total
        if markup_pct > 0 or tax_pct > 0:
            marked_up, tax_amount, with_tax = apply_markup_and_tax(
                total_cost,
                markup_pct,
                tax_pct,
            )
            total_cost = with_tax
            cost_model.meta["markup_amount"] = round(marked_up - (total_cost - tax_amount), 2)
            cost_model.meta["tax_amount"] = round(tax_amount, 2)
        
        cost_model.total_cost = round(total_cost, 2)
        cost_model.total_cost_by_currency[currency.value] = round(total_cost, 2)
        
        # Calculate base currency totals
        total_cost_base = sum(item.extended_cost_in_base_currency or 0.0 for item in cost_model.items)
        cost_model.total_cost_by_currency[catalog.currency.value] = round(total_cost_base, 2)
        
        # Populate FX metadata
        cost_model.meta.update({
            "base_currency": catalog.currency.value,
            "target_currency": currency.value,
            "total_cost_base": round(total_cost_base, 2),
            "total_cost_target": round(total_cost, 2),
        })
        
        # Record FX rate if conversion happened
        if catalog.currency != currency:
            # Infer rate from total or lookup (lookup is cleaner but logic is hidden in catalog.convert)
            # We can calculate effective rate:
            effective_rate = round(total_cost / total_cost_base, 6) if total_cost_base > 0 else 0.0
            cost_model.meta["fx_rate_used"] = effective_rate
            cost_model.meta["fx_conversion_note"] = f"Converted from {catalog.currency.value} to {currency.value}"

        # Create rollups per scope
        # Use boq_model scopes to map ID to name if possible
        scope_map = {s.scope_id: s.scope_name for s in boq_model.scopes}
        
        for scope_key, scope_items in items_by_scope.items():
            scope_total = sum(item.extended_cost for item in scope_items)
            
            # Breakdown by type
            by_type: Dict[str, float] = {}
            for item in scope_items:
                by_type[item.boq_item_type] = by_type.get(item.boq_item_type, 0) + item.extended_cost
            
            rollup = CostRollup(
                scope_id=scope_key,
                scope_name=scope_map.get(scope_key, scope_key), # Fallback to ID
                item_count=len(scope_items),
                total_cost=round(scope_total, 2),
                currency=currency,
                by_type=by_type,
            )
            cost_model.rollups.append(rollup)
        
        # Compute model hash
        item_hashes = [item.id for item in cost_model.items]
        hash_str = "".join(item_hashes) + catalog.version + currency.value + str(cost_model.total_cost)
        cost_model.model_hash = hashlib.sha256(hash_str.encode()).hexdigest()[:16]
        
        # Cache
        self.cache.put(cache_key, cost_model)
        
        # Build response
        response = self._model_to_response(cost_model)
        
        return cost_model, response
    
    def estimate_costs(
        self,
        boq_model: BoQModel,
        request: CostRequest,
    ) -> Tuple[CostModel, CostResponse]:
        """Adapter for CostRequest."""
        return self.estimate_cost(
            boq_model=boq_model,
            catalog=None, # Will resolve by version
            currency=request.currency,
            markup_pct=request.markup_pct,
            tax_pct=request.tax_pct,
            catalog_overrides=request.catalog_overrides,
            catalog_version=request.catalog_version
        )
    
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
        
        # 1. Construct compliant metadata
        # Must match CostModel-strict keys in media_v2
        meta = {
            "total_cost": cost_model.total_cost,
            "currency": cost_model.currency.value,
            "item_count": len(cost_model.items),
            "model_hash": cost_model.model_hash,
            "catalog_version": cost_model.catalog_version,
            "base_currency": cost_model.meta.get("base_currency"),
            "total_cost_base": cost_model.meta.get("total_cost_base"),
            # Optional extras
            "warnings": cost_model.meta.get("warnings", []),
            "markup_amount": cost_model.meta.get("markup_amount", 0.0),
            "tax_amount": cost_model.meta.get("tax_amount", 0.0),
        }
        
        # 2. Validate compliance via DerivedArtifact (fail-fast)
        # We need to import DerivedArtifact inside or have it imported.
        # It's not imported yet. I should add import or just use dict if I can't easily add import here.
        # Better to add import for safety. 
        # For now, I'll rely on the logic being correct, but technically I should test it against the model definition.
        # Let's assume validation happens in the actual registration call (which is stubbed here).
        # But to be robust:
        
        from engines.media_v2.models import DerivedArtifact
        
        # Context usually provides tenant/env
        tenant_id = (context or {}).get("tenant_id", "default_tenant")
        env = (context or {}).get("env", "dev")
        
        try:
            DerivedArtifact(
                id=artifact_id,
                parent_asset_id=boq_model_id, # Link to BoQ (or Semantic Model?? BoQ is usually derived artifact too. Parent asset is usually the uploaded file. BoQ is derived.)
                # Actually, cost is derived from BoQ. BoQ is derived from Semantic. Semantic is derived from CAD.
                # So parent_asset_id should ideally be the root CAD asset ID.
                # But here we only have boq_model_id. 
                # Let's assume boq_model_id refers to an artifact, so parent is that artifact? No, DerivedArtifact.parent_asset_id refers to MediaAsset.
                # We'll use a placeholder or pass it in context. For now, use boq_model_id as best-effort link.
                tenant_id=tenant_id,
                env=env,
                kind="cost_model",
                uri=f"cost://{artifact_id}",
                meta=meta
            )
        except ValueError as e:
            # Re-raise with context
            raise ValueError(f"Cost artifact metadata validation failed: {str(e)}")
            
        # TODO: Real registration with media_v2 service
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
