"""
FastAPI routes for plan-of-works generation.

POST /cad/plan_of_work
- Input: cost_model_id, template_version, productivity_config
- Output: PlanResponse with task counts, critical path, artifact ID
"""

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from engines.plan_of_work.models import PlanResponse
from engines.plan_of_work.service import get_plan_service
from engines.media_v2.models import ArtifactMetadata, RequestContext

router = APIRouter(prefix="/cad", tags=["cad"])


class PlanOfWorkRequest(BaseModel):
    """Request to generate plan from cost data."""

    cost_model_id: str = Field(
        ...,
        description="ID of the cost artifact to plan",
        example="cost_001_abc123",
    )
    template_version: Optional[str] = Field(
        default="1.0.0",
        description="Version of task templates to use",
        example="1.0.0",
    )
    productivity_config: dict = Field(
        default_factory=dict,
        description="Productivity rates per task type (higher = faster)",
        example={"wall": 1.2, "door": 1.5},
    )
    context: Optional[RequestContext] = Field(
        default=None,
        description="Request context for tracking/audit",
    )


class PlanOfWorkResponseBody(BaseModel):
    """Response from plan generation endpoint."""

    plan_artifact_id: str = Field(
        ...,
        description="ID of the registered plan artifact",
        example="plan_001_def456",
    )
    plan_response: PlanResponse = Field(
        ...,
        description="Full plan generation results",
    )
    metadata: ArtifactMetadata = Field(
        ...,
        description="Artifact metadata including template_version, task_counts, critical_path",
    )


@router.post("/plan_of_work", response_model=PlanOfWorkResponseBody, status_code=201)
async def generate_plan_of_work(
    request: PlanOfWorkRequest = Body(
        ...,
        description="Plan-of-works generation request",
    ),
) -> PlanOfWorkResponseBody:
    """
    Generate plan-of-works from cost estimate.

    Applies task templates to cost items, generates dependencies based on
    logical sequencing rules, computes critical path and schedule.

    Returns plan artifact with tasks, dependencies, schedule, and critical path analysis.

    Args:
        request: PlanOfWorkRequest with cost_model_id, template_version, productivity_config

    Returns:
        PlanOfWorkResponseBody with artifact ID, plan results, metadata

    Raises:
        404: Cost model not found
        422: Invalid template version or parameters
        500: Internal service error
    """
    try:
        service = get_plan_service()

        # TODO: In production, would fetch actual cost model from media_v2
        # For now, service will handle it internally
        plan_model, plan_response = service.generate_plan(
            cost_model=None,  # Would fetch from media_v2
            template_version=request.template_version or "1.0.0",
            productivity_config=request.productivity_config,
        )

        # Register plan artifact
        artifact_id = service.register_artifact(
            cost_model_id=request.cost_model_id,
            plan_model=plan_model,
            template_version=request.template_version or "1.0.0",
            context=request.context,
        )

        # Build response
        return PlanOfWorkResponseBody(
            plan_artifact_id=artifact_id,
            plan_response=plan_response,
            metadata=ArtifactMetadata(
                artifact_id=artifact_id,
                artifact_kind="plan_of_work",
                source_artifact_id=request.cost_model_id,
                version="1.0",
                content_hash=plan_model.model_hash or "",
                metadata={
                    "template_version": request.template_version or "1.0.0",
                    "task_count": plan_response.task_count,
                    "critical_path_days": plan_response.critical_path_duration_days,
                    "task_count_by_category": plan_response.task_count_by_category,
                    "productivity_config": request.productivity_config,
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
            detail=f"Cost model {request.cost_model_id} not found: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation failed: {str(e)}",
        )
