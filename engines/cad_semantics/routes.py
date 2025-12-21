"""
FastAPI routes for CAD semantic classification.

POST /cad/semantics
- Input: cad_model_id, rule_version, optional rule_overrides
- Output: SemanticResponse with classification results, spatial graph, artifact ID
"""

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from engines.cad_semantics.models import SemanticResponse, SemanticType
from engines.cad_semantics.service import get_semantic_service
from engines.media_v2.models import ArtifactMetadata, RequestContext

router = APIRouter(prefix="/cad", tags=["cad"])


class SemanticizeRequest(BaseModel):
    """Request to semanticize a CAD model."""

    cad_model_id: str = Field(
        ...,
        description="ID of the CAD ingest artifact to semanticize",
        example="cad_001_abc123",
    )
    rule_version: Optional[str] = Field(
        default="latest",
        description="Version of classification rules to apply",
        example="1.0",
    )
    rule_overrides: Optional[dict] = Field(
        default=None,
        description="Optional overrides for classification rules",
        example={"wall_layer_pattern": "WALL_.*"},
    )
    context: Optional[RequestContext] = Field(
        default=None,
        description="Request context for tracking/audit",
    )


class SemanticizeResponse(BaseModel):
    """Response from semanticize endpoint."""

    semantic_artifact_id: str = Field(
        ...,
        description="ID of the registered semantic artifact",
        example="sem_001_def456",
    )
    semantic_response: SemanticResponse = Field(
        ...,
        description="Full semantic classification results",
    )
    metadata: ArtifactMetadata = Field(
        ...,
        description="Artifact metadata including rule version, content hash",
    )


@router.post("/semantics", response_model=SemanticizeResponse, status_code=201)
async def semanticize_cad_model(
    request: SemanticizeRequest = Body(
        ...,
        description="Semantic classification request",
    ),
) -> SemanticizeResponse:
    """
    Semantically classify a CAD model.

    Applies classification rules to identify semantic types (walls, doors, etc.),
    infers building levels, constructs spatial graph, and computes statistics.

    Returns semantic artifact with classification results, spatial relationships,
    and element counts by type.

    Args:
        request: SemanticizeRequest with cad_model_id, rule_version, overrides

    Returns:
        SemanticizeResponse with artifact ID, semantic results, metadata

    Raises:
        404: CAD model not found
        422: Invalid rule version or overrides
        500: Internal service error
    """
    try:
        service = get_semantic_service()

        # TODO: In production, would fetch actual CAD model from media_v2
        # For now, service will handle it internally
        semantic_model, semantic_response = service.semanticize(
            cad_model_id=request.cad_model_id,
            rule_version=request.rule_version or "latest",
            rule_overrides=request.rule_overrides or {},
        )

        # Register semantic artifact
        artifact_id = service.register_artifact(
            cad_model_id=request.cad_model_id,
            semantic_model=semantic_model,
            rule_version=request.rule_version or "latest",
            context=request.context,
        )

        # Build response
        return SemanticizeResponse(
            semantic_artifact_id=artifact_id,
            semantic_response=semantic_response,
            metadata=ArtifactMetadata(
                artifact_id=artifact_id,
                artifact_kind="cad_semantics",
                source_artifact_id=request.cad_model_id,
                version="1.0",
                content_hash=semantic_model.model_hash,
                metadata={
                    "rule_version": request.rule_version or "latest",
                    "element_count": semantic_response.element_count,
                    "wall_count": semantic_response.wall_count,
                    "door_count": semantic_response.door_count,
                    "window_count": semantic_response.window_count,
                    "slab_count": semantic_response.slab_count,
                    "column_count": semantic_response.column_count,
                    "room_count": semantic_response.room_count,
                    "stair_count": semantic_response.stair_count,
                    "spatial_graph_edge_count": semantic_response.spatial_graph_edge_count,
                    "level_count": semantic_response.level_count,
                    "graph_hash": semantic_model.spatial_graph.graph_hash,
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
            detail=f"CAD model {request.cad_model_id} not found: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic classification failed: {str(e)}",
        )


@router.get("/semantics/{semantic_artifact_id}", response_model=SemanticResponse)
async def get_semantic_artifact(semantic_artifact_id: str) -> SemanticResponse:
    """
    Retrieve a previously classified semantic artifact.

    Args:
        semantic_artifact_id: ID of semantic artifact

    Returns:
        SemanticResponse with cached classification results

    Raises:
        404: Artifact not found
    """
    try:
        service = get_semantic_service()
        # TODO: Implement artifact retrieval from media_v2
        semantic_response = service.get_artifact(semantic_artifact_id)
        return semantic_response
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Semantic artifact {semantic_artifact_id} not found",
        )
