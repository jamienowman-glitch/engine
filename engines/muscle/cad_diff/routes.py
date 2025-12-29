"""
CAD Diff Routes - HTTP endpoints for diff computation.

Routes for computing diffs between artifact versions.
"""

from fastapi import APIRouter

from .models import DiffRequest, DiffResponse

router = APIRouter()


@router.post("/cad/diff", response_model=DiffResponse)
async def compute_diff(request: DiffRequest) -> DiffResponse:
    """
    Compute diff between two artifact versions.
    
    Supports comparison at:
    - cad_semantics: Element-level changes
    - boq_quantities: Quantity changes
    - boq_cost: Cost impacts  
    - plan_of_work: Task schedule impacts
    
    Note: Route requires integration with media service for artifact loading.
    """
    # Placeholder for route integration
    raise NotImplementedError("Route requires artifact loading integration")
