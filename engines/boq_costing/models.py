"""
BoQ Costing Models - Cost item and catalog schemas.

Defines:
- CostItem: Priced BoQ item with rate, currency, totals
- CostCatalog: Rate library with versioning
- CostModel: Complete cost estimate with rollups
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Currency(str, Enum):
    """Supported currencies (TODO: USD as default per phase doc)."""
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class CostAssumption(BaseModel):
    """Cost assumption/note."""
    key: str  # "markup", "tax", "discount", "contingency", etc.
    value: float  # Percentage or fixed amount
    applied: bool = True


class RateRecord(BaseModel):
    """Single rate in catalog."""
    element_type: str  # "wall", "door", "slab", etc.
    unit_type: str  # "m2", "count", "m3", etc.
    unit_rate: float  # Cost per unit
    currency: Currency = Currency.USD
    markup_pct: float = 0.0
    description: str = ""


class CostCatalog(BaseModel):
    """Rate catalog with versioning."""
    version: str = "1.0.0"
    currency: Currency = Currency.USD  # Default currency
    fx_rates: Dict[str, float] = Field(default_factory=dict)  # FX table: "GBP"->0.73, etc.
    rates: List[RateRecord] = Field(default_factory=list)
    markup_pct: float = 0.0  # Catalog-level markup
    tax_pct: float = 0.0  # Catalog-level tax
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    def get_rate(
        self,
        element_type: str,
        unit_type: str,
        fallback: float = 0.0,
    ) -> Optional[float]:
        """Get unit rate from catalog."""
        for record in self.rates:
            if record.element_type == element_type and record.unit_type == unit_type:
                return record.unit_rate
        return fallback if fallback is not None else None
    
    def convert_currency(self, amount: float, from_curr: Currency, to_curr: Currency) -> float:
        """Convert amount between currencies using FX table."""
        if from_curr == to_curr:
            return amount
        
        # Get FX rate
        fx_key = f"{from_curr.value}/{to_curr.value}"
        if fx_key not in self.fx_rates:
            # Try reverse
            fx_key = f"{to_curr.value}/{from_curr.value}"
            if fx_key in self.fx_rates:
                rate = 1.0 / self.fx_rates[fx_key]
            else:
                # Default to 1:1 if not found
                rate = 1.0
        else:
            rate = self.fx_rates[fx_key]
        
        return amount * rate


class CostItem(BaseModel):
    """Single cost item."""
    id: str  # Deterministic hash-based ID
    
    # Reference
    boq_item_id: str  # Source BoQ item
    boq_item_type: str  # wall, door, etc.
    boq_item_quantity: float  # From BoQ
    boq_item_unit: str  # From BoQ (m2, count, etc.)
    
    # Costing
    unit_rate: float  # Cost per unit
    currency: Currency = Currency.USD
    extended_cost: float  # quantity × unit_rate
    extended_cost_in_base_currency: Optional[float] = None
    
    # Assumptions
    assumptions: List[CostAssumption] = Field(default_factory=list)
    category: Optional[str] = None  # "structure", "interior", etc.
    
    # Metadata
    source_catalog_version: str = "1.0.0"
    calc_version: str = "1.0.0"
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CostRollup(BaseModel):
    """Cost summary for a scope."""
    scope_id: Optional[str] = None
    scope_name: str = "Total"
    
    item_count: int = 0
    total_cost: float = 0.0
    currency: Currency = Currency.USD
    
    by_type: Dict[str, float] = Field(default_factory=dict)  # Subtotals by element type
    meta: Dict[str, Any] = Field(default_factory=dict)


class CostModel(BaseModel):
    """Complete cost estimate."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Source reference
    boq_model_id: str
    
    # Cost data
    items: List[CostItem] = Field(default_factory=list)
    rollups: List[CostRollup] = Field(default_factory=list)
    
    # Summary
    total_cost: float = 0.0
    total_cost_by_currency: Dict[str, float] = Field(default_factory=dict)
    
    # Configuration
    currency: Currency = Currency.USD
    catalog_version: str = "1.0.0"
    markup_pct: float = 0.0
    tax_pct: float = 0.0
    
    # Determinism
    model_hash: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class CostRequest(BaseModel):
    """Request to generate costs from BoQ."""
    boq_model_id: str
    catalog_version: str = "1.0.0"
    currency: Currency = Currency.USD
    markup_pct: float = 0.0
    tax_pct: float = 0.0
    catalog_overrides: Optional[Dict[str, float]] = None


class CostResponse(BaseModel):
    """Response from cost generation."""
    cost_artifact_id: str
    cost_model_id: str
    total_cost: float
    currency: Currency
    item_count: int
    rollup_count: int
    catalog_version: str
    model_hash: str
    created_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)
