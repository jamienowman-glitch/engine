"""Service layer to build CadGanttView and CadOverlayView from upstream CAD engines."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from engines.cad_viewer.models import CadGanttView, CadOverlayView, GanttTask, OverlayElement
from engines.plan_of_work.service import get_plan_service
from engines.boq_costing.service import get_costing_service
from engines.boq_quantities.service import get_boq_service


class CadViewerError(Exception):
    pass


class MissingArtifactError(CadViewerError):
    def __init__(self, missing_kinds: List[str]):
        super().__init__(f"Missing required artifacts: {', '.join(missing_kinds)}")
        self.missing_kinds = missing_kinds


class CadViewerService:
    """Build read-only view-models from CAD pipeline engines.

    Integrates with:
      - plan_of_work engine for schedule/tasks
      - boq_quantities engine for element quantities
      - boq_costing engine for cost breakdown

    The service reads models from upstream engines and maps them
    deterministically into CadGanttView and CadOverlayView.
    """

    def __init__(self, plan_service=None, boq_service=None, costing_service=None):
        self.plan_svc = plan_service or get_plan_service()
        self.boq_svc = boq_service or get_boq_service()
        self.cost_svc = costing_service or get_costing_service()

    def _deterministic_hash(self, parts: List[str]) -> str:
        """Generate deterministic SHA256 hash from ordered string parts."""
        h = hashlib.sha256()
        for p in parts:
            if p is None:
                p = ""
            h.update(str(p).encode("utf-8"))
            h.update(b"|")
        return h.hexdigest()

    def build_gantt_view(self, project_id: str, cost_model_id: str, context: Optional[Dict[str, Any]] = None) -> CadGanttView:
        """Build deterministic Gantt view from plan_of_work and cost_model.
        
        Args:
            project_id: Project identifier
            cost_model_id: Cost model ID (used to fetch plan and costing data)
            context: Optional RequestContext with tenant_id, env, request_id
            
        Returns:
            CadGanttView with tasks and deterministic hashes
        """
        # Fetch plan from plan_of_work service using cost_model_id
        try:
            plan = self.plan_svc.generate_plan(cost_model_id, template_version="1.0.0")
        except Exception as e:
            raise CadViewerError(f"Failed to fetch plan for cost_model {cost_model_id}: {e}")
        
        if not plan or not plan.tasks:
            raise MissingArtifactError(["plan_of_work"])

        # Build GanttTask entries from plan tasks
        tasks = []
        for t in plan.tasks:
            gt = GanttTask(
                id=t.id,
                name=t.name,
                trade=getattr(t, "category", None) or "unknown",
                level="L1",  # Default level; CAD semantics would refine this
                zone="Z1",   # Default zone; CAD semantics would refine this
                start_date=None,  # Computed from early_start_day in plan
                end_date=None,    # Computed from early_finish_day in plan
                duration_days=t.duration_days,
                predecessors=[d.predecessor_task_id for d in (t.dependencies or [])],
                boq_refs=t.boq_refs or [],
                cost_refs=t.cost_refs or [],
                meta=t.meta or {},
            )
            
            # Deterministic task hash: plan hash + task ID + name
            plan_hash = plan.model_hash if hasattr(plan, "model_hash") else str(plan.id)
            parts = [plan_hash, gt.id, gt.name, str(gt.duration_days)]
            gt.hash = self._deterministic_hash(parts)
            tasks.append(gt)

        # Build CadGanttView
        view = CadGanttView(
            project_id=project_id,
            cad_model_id=cost_model_id,
            tasks=tasks,
            meta={
                "source_engine": "plan_of_work",
                "plan_model_hash": plan.model_hash if hasattr(plan, "model_hash") else str(plan.id),
            },
        )
        if context:
            view.meta.update({
                "tenant_id": context.get("tenant_id"),
                "env": context.get("env"),
                "request_id": context.get("request_id"),
            })
        
        # View-level deterministic hash
        plan_hash = plan.model_hash if hasattr(plan, "model_hash") else str(plan.id)
        view.view_hash = self._deterministic_hash([
            plan_hash,
            cost_model_id,
            project_id,
        ])
        
        return view

    def build_overlay_view(self, project_id: str, cost_model_id: str, context: Optional[Dict[str, Any]] = None) -> CadOverlayView:
        """Build deterministic overlay view from boq_quantities and cost_model.
        
        Args:
            project_id: Project identifier
            cost_model_id: Cost model ID (used to fetch boq and costing data)
            context: Optional RequestContext with tenant_id, env, request_id
            
        Returns:
            CadOverlayView with elements and deterministic hashes
        """
        # Fetch cost model from costing service
        try:
            cost_model = self.cost_svc.get_cost_model(cost_model_id)
        except Exception as e:
            raise CadViewerError(f"Failed to fetch cost_model {cost_model_id}: {e}")
        
        if not cost_model:
            raise MissingArtifactError(["cost_model"])

        # Build OverlayElement entries from cost model items
        elements = []
        cost_hash = cost_model.model_hash if hasattr(cost_model, "model_hash") else str(cost_model.id)
        
        if cost_model.items:
            for item in cost_model.items:
                oe = OverlayElement(
                    id=item.id,
                    name=item.boq_item_id or f"Item {item.id}",
                    level="L1",  # Default; would be refined from semantics
                    zone="Z1",   # Default; would be refined from semantics
                    trade=item.boq_item_type or "unknown",
                    quantity=item.boq_item_quantity,
                    unit=item.boq_item_unit,
                    cost=item.extended_cost,
                    meta={},
                )
                
                # Deterministic element hash: cost_model hash + item ID + name
                parts = [cost_hash, oe.id, oe.name, str(oe.quantity), oe.unit, str(oe.cost)]
                oe.hash = self._deterministic_hash(parts)
                elements.append(oe)

        # Build CadOverlayView
        view = CadOverlayView(
            project_id=project_id,
            cad_model_id=cost_model_id,
            elements=elements,
            meta={
                "source_engine": "boq_costing",
                "cost_model_hash": cost_hash,
            },
        )
        if context:
            view.meta.update({
                "tenant_id": context.get("tenant_id"),
                "env": context.get("env"),
                "request_id": context.get("request_id"),
            })
        
        # View-level deterministic hash
        view.view_hash = self._deterministic_hash([
            cost_hash,
            cost_model_id,
            project_id,
        ])
        
        return view


# Module-level default service
_default_cad_viewer: Optional[CadViewerService] = None


def get_cad_viewer_service(
    plan_service=None,
    boq_service=None,
    costing_service=None,
) -> CadViewerService:
    """Get the default CAD viewer service (singleton).
    
    Args:
        plan_service: Optional PlanOfWorkService override for testing
        boq_service: Optional BoQService override for testing
        costing_service: Optional CostingService override for testing
        
    Returns:
        CadViewerService instance
    """
    global _default_cad_viewer
    if _default_cad_viewer is None:
        _default_cad_viewer = CadViewerService(
            plan_service=plan_service,
            boq_service=boq_service,
            costing_service=costing_service,
        )
    return _default_cad_viewer


def set_cad_viewer_service(service: CadViewerService) -> None:
    """Override the default CAD viewer service (for testing)."""
    global _default_cad_viewer
    _default_cad_viewer = service
