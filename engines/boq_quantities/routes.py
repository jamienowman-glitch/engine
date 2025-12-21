"""
FastAPI routes for BoQ quantity generation.

POST /cad/boq_quantities
- Input: semantic_model_id, calc_version, calculation parameters
- Output: BoQResponse with item counts, scopes, artifact ID
"""

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from engines.boq_quantities.models import BoQResponse
from engines.boq_quantities.service import get_boq_service
from engines.media_v2.models import ArtifactMetadata, RequestContext

router = APIRouter(prefix="/cad", tags=["cad"])


class BoQQuantitiesRequest(BaseModel):
    """Request to generate BoQ from semantic model."""

    semantic_model_id: str = Field(
        ...,
        description="ID of the semantic artifact to quantify",
        example="sem_001_abc123",
    )
    calc_version: Optional[str] = Field(
        default="1.0.0",
        description="Version of BoQ calculation rules",
        example="1.0.0",
    )
    calc_params: dict = Field(
        default_factory=dict,
        description="Calculation parameters (wall thickness, slab thickness, etc.)",
        example={"wall_thickness_mm": 250, "slab_thickness_mm": 200},
    )
    context: Optional[RequestContext] = Field(
        default=None,
        description="Request context for tracking/audit",
    )


class BoQQuantitiesResponseBody(BaseModel):
    """Response from BoQ generation endpoint."""

    boq_artifact_id: str = Field(
        ...,
        description="ID of the registered BoQ artifact",
        example="boq_001_def456",
    )
    boq_response: BoQResponse = Field(
        ...,
        description="Full BoQ generation results",
    )
    metadata: ArtifactMetadata = Field(
        ...,
        description="Artifact metadata including calc_version, item counts",
    )


@router.post("/boq_quantities", response_model=BoQQuantitiesResponseBody, status_code=201)
async def generate_boq_quantities(
    request: BoQQuantitiesRequest = Body(
        ...,
        description="BoQ generation request",
    ),
) -> BoQQuantitiesResponseBody:
    """
    Generate bill of quantities from semantic model.

    Applies quantity formulas to semantic elements, calculates areas/volumes/counts,
    aggregates by scope (level/zone), and produces deterministic BoQ items.

    Returns BoQ artifact with item list, scopes, and statistics.

    Args:
        request: BoQQuantitiesRequest with semantic_model_id, calc_version, params

    Returns:
        BoQQuantitiesResponseBody with artifact ID, BoQ results, metadata

    Raises:
        404: Semantic model not found
        422: Invalid calculation parameters
        500: Internal service error
    """
    try:
        service = get_boq_service()

        # TODO: In production, would fetch actual semantic model from media_v2
        # For now, service will handle it internally
        boq_model, boq_response = service.quantify(
            semantic_model=None,  # Would fetch from media_v2
            calc_version=request.calc_version or "1.0.0",
            calc_params=request.calc_params,
        )

        # Register BoQ artifact
        artifact_id = service.register_artifact(
            semantic_model_id=request.semantic_model_id,
            boq_model=boq_model,
            calc_version=request.calc_version or "1.0.0",
            context=request.context,
        )

        # Build response
        return BoQQuantitiesResponseBody(
            boq_artifact_id=artifact_id,
            boq_response=boq_response,
            metadata=ArtifactMetadata(
                artifact_id=artifact_id,
                artifact_kind="boq_quantities",
                source_artifact_id=request.semantic_model_id,
                version="1.0",
                content_hash=boq_model.model_hash or "",
                metadata={
                    "calc_version": request.calc_version or "1.0.0",
                    "item_count": boq_response.item_count,
                    "scope_count": boq_response.scope_count,
                    "item_count_by_type": boq_response.item_count_by_type,
                    "calc_params": request.calc_params,
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
            detail=f"Semantic model {request.semantic_model_id} not found: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BoQ generation failed: {str(e)}",
        )
