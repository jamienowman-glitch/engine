"""
FastAPI routes for BoQ costing.

POST /cad/boq_cost
- Input: boq_model_id, catalog_version, currency, markup/tax parameters
- Output: CostResponse with totals, rollups, artifact ID
"""

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from engines.boq_costing.models import Currency, CostResponse
from engines.boq_costing.service import get_costing_service
from engines.media_v2.models import ArtifactMetadata, RequestContext

router = APIRouter(prefix="/cad", tags=["cad"])


class BoQCostRequest(BaseModel):
    """Request to generate costs from BoQ."""

    boq_model_id: str = Field(
        ...,
        description="ID of the BoQ artifact to cost",
        example="boq_001_abc123",
    )
    catalog_version: Optional[str] = Field(
        default="1.0.0",
        description="Version of cost catalog to use",
        example="1.0.0",
    )
    currency: Currency = Field(
        default=Currency.USD,
        description="Target currency for costs",
        example="USD",
    )
    markup_pct: float = Field(
        default=0.0,
        description="Markup percentage to apply",
        example=15.0,
    )
    tax_pct: float = Field(
        default=0.0,
        description="Tax percentage to apply",
        example=10.0,
    )
    catalog_overrides: Optional[dict] = Field(
        default=None,
        description="Override specific element type rates",
        example={"wall": 175.0},
    )
    context: Optional[RequestContext] = Field(
        default=None,
        description="Request context for tracking/audit",
    )


class BoQCostResponseBody(BaseModel):
    """Response from cost generation endpoint."""

    cost_artifact_id: str = Field(
        ...,
        description="ID of the registered cost artifact",
        example="cost_001_def456",
    )
    cost_response: CostResponse = Field(
        ...,
        description="Full cost generation results",
    )
    metadata: ArtifactMetadata = Field(
        ...,
        description="Artifact metadata including catalog_version, currency, totals",
    )


@router.post("/boq_cost", response_model=BoQCostResponseBody, status_code=201)
async def generate_boq_costs(
    request: BoQCostRequest = Body(
        ...,
        description="BoQ costing request",
    ),
) -> BoQCostResponseBody:
    """
    Generate cost estimate from bill of quantities.

    Applies cost catalog (with optional overrides) to BoQ items, converts to target
    currency, applies markup/tax, and produces deterministic cost totals and rollups.

    Returns cost artifact with line items, scopes, and complete financial summary.

    Args:
        request: BoQCostRequest with boq_model_id, catalog_version, currency, params

    Returns:
        BoQCostResponseBody with artifact ID, cost results, metadata

    Raises:
        404: BoQ model not found
        422: Invalid catalog version or parameters
        500: Internal service error
    """
    try:
        service = get_costing_service()

        # TODO: In production, would fetch actual BoQ model from media_v2
        # For now, service will handle it internally
        cost_model, cost_response = service.estimate_cost(
            boq_model=None,  # Would fetch from media_v2
            currency=request.currency,
            markup_pct=request.markup_pct,
            tax_pct=request.tax_pct,
            catalog_overrides=request.catalog_overrides or {},
        )

        # Register cost artifact
        artifact_id = service.register_artifact(
            boq_model_id=request.boq_model_id,
            cost_model=cost_model,
            catalog_version=request.catalog_version or "1.0.0",
            context=request.context,
        )

        # Build response
        return BoQCostResponseBody(
            cost_artifact_id=artifact_id,
            cost_response=cost_response,
            metadata=ArtifactMetadata(
                artifact_id=artifact_id,
                artifact_kind="boq_cost",
                source_artifact_id=request.boq_model_id,
                version="1.0",
                content_hash=cost_model.model_hash or "",
                metadata={
                    "catalog_version": request.catalog_version or "1.0.0",
                    "currency": request.currency.value,
                    "total_cost": cost_response.total_cost,
                    "item_count": cost_response.item_count,
                    "rollup_count": cost_response.rollup_count,
                    "markup_pct": request.markup_pct,
                    "tax_pct": request.tax_pct,
                },
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BoQ model {request.boq_model_id} not found: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cost generation failed: {str(e)}",
        )
