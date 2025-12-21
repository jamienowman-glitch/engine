"""
Plan-of-Works Service - Generate tasks and compute critical path.

Implements:
- Task generation from BoQ via templates
- DAG construction with dependency checking
- Critical path computation
- Service with caching by cost_id + template_version
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from engines.boq_costing.models import CostModel, CostItem
from engines.plan_of_work.models import (
    PlanDependency,
    PlanOfWork,
    PlanResponse,
    PlanTask,
    TaskCategory,
    DependencyType,
)
from engines.plan_of_work.templates import get_template, get_dependency_order


class PlanCache:
    """In-memory cache for plan models."""
    
    def __init__(self, max_entries: int = 50):
        self.cache: Dict[str, PlanOfWork] = {}
        self.max_entries = max_entries
    
    def cache_key(self, cost_model_id: str, template_version: str, params_hash: str) -> str:
        """Generate cache key."""
        return f"{cost_model_id}:{template_version}:{params_hash}"
    
    def get(self, key: str) -> Optional[PlanOfWork]:
        """Retrieve cached model."""
        return self.cache.get(key)
    
    def put(self, key: str, model: PlanOfWork) -> None:
        """Store model in cache."""
        if len(self.cache) >= self.max_entries:
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[key] = model
    
    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()


class PlanOfWorkService:
    """Generate plans from BoQ/cost data."""
    
    def __init__(self):
        self.cache = PlanCache()
    
    def _params_hash(self, params: Dict[str, Any]) -> str:
        """Hash productivity parameters."""
        if not params:
            return "default"
        items = sorted(params.items())
        key = str(items)
        return hashlib.sha256(key.encode()).hexdigest()[:8]
    
    def generate_plan(
        self,
        cost_model: CostModel,
        template_version: str = "1.0.0",
        productivity_config: Optional[Dict[str, float]] = None,
    ) -> Tuple[PlanOfWork, PlanResponse]:
        """
        Generate plan from cost model.
        
        Args:
            cost_model: Cost model with BoQ items and pricing
            template_version: Version of task templates
            productivity_config: Productivity rates (higher = faster)
        
        Returns:
            (PlanOfWork, PlanResponse)
        """
        params = productivity_config or {}
        
        # Check cache
        cache_key = self.cache.cache_key(
            cost_model.boq_model_id,
            template_version,
            self._params_hash(params),
        )
        cached = self.cache.get(cache_key)
        if cached:
            response = self._model_to_response(cached)
            return cached, response
        
        # Initialize plan
        plan = PlanOfWork(
            cost_model_id=cost_model.id,
            template_version=template_version,
            productivity_config=params,
        )
        
        # Generate tasks from cost items
        task_id_map: Dict[str, str] = {}  # boq_type -> task_id
        default_productivity = params.get("default", 1.0)
        
        for cost_item in cost_model.items:
            boq_type = cost_item.boq_item_type
            template = get_template(boq_type)
            
            # Estimate duration
            productivity = params.get(boq_type, default_productivity)
            duration = template.estimate_duration(
                cost_item.boq_item_quantity,
                productivity,
            )
            
            # Create task
            task_id = f"task_{boq_type}_{hashlib.sha256(cost_item.boq_item_id.encode()).hexdigest()[:8]}"
            task = PlanTask(
                id=task_id,
                name=template.task_name,
                description=template.task_description,
                category=template.category,
                duration_days=round(duration, 1),
                resource_tags=template.resource_tags,
                cost_refs=[cost_item.id],
                boq_refs=[cost_item.boq_item_id],
                template_used=template.boq_type,
                productivity_assumption=f"rate={productivity}x",
            )
            
            plan.tasks.append(task)
            task_id_map[boq_type] = task_id
        
        # Build dependencies
        category_to_tasks: Dict[TaskCategory, List[str]] = {}
        for task in plan.tasks:
            if task.category not in category_to_tasks:
                category_to_tasks[task.category] = []
            category_to_tasks[task.category].append(task.id)
        
        # Link tasks based on predecessor categories
        for task in plan.tasks:
            template = get_template(task.template_used)
            for pred_category in template.predecessor_categories:
                if pred_category in category_to_tasks:
                    for pred_task_id in category_to_tasks[pred_category]:
                        if pred_task_id != task.id:
                            dep = PlanDependency(
                                predecessor_task_id=pred_task_id,
                                successor_task_id=task.id,
                                dependency_type=DependencyType.FINISH_TO_START,
                            )
                            task.dependencies.append(dep)
                            plan.all_dependencies.append(dep)
        
        # Detect cycles (simplified)
        if self._has_cycle(plan.tasks):
            plan.meta["warnings"] = ["Cycle detected in task graph"]
        
        # Compute schedule (forward pass)
        self._compute_schedule(plan.tasks, plan.all_dependencies)
        
        # Compute critical path
        self._compute_critical_path(plan)
        
        # Sort tasks deterministically
        plan.tasks.sort(key=lambda t: (t.category.value, t.id))
        
        # Statistics
        plan.task_count = len(plan.tasks)
        type_counts: Dict[str, int] = {}
        for task in plan.tasks:
            key = task.category.value
            type_counts[key] = type_counts.get(key, 0) + 1
        plan.task_count_by_category = type_counts
        
        # Compute model hash
        task_hashes = [hashlib.sha256(task.id.encode()).hexdigest() for task in plan.tasks]
        hash_str = "".join(task_hashes) + template_version
        plan.model_hash = hashlib.sha256(hash_str.encode()).hexdigest()[:16]
        
        # Cache
        self.cache.put(cache_key, plan)
        
        # Build response
        response = self._model_to_response(plan)
        
        return plan, response
    
    def _has_cycle(self, tasks: List[PlanTask]) -> bool:
        """Detect cycles in dependency graph (simplified DFS)."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            # Find successors
            for task in tasks:
                if task.id == task_id:
                    for dep in task.dependencies:
                        successor = dep.successor_task_id
                        if successor not in visited:
                            if dfs(successor):
                                return True
                        elif successor in rec_stack:
                            return True
            
            rec_stack.discard(task_id)
            return False
        
        for task in tasks:
            if task.id not in visited:
                if dfs(task.id):
                    return True
        
        return False
    
    def _compute_schedule(self, tasks: List[PlanTask], dependencies: List[PlanDependency]) -> None:
        """Compute early start/finish times (forward pass)."""
        # Build dependency map
        pred_map: Dict[str, List[str]] = {}
        for dep in dependencies:
            if dep.successor_task_id not in pred_map:
                pred_map[dep.successor_task_id] = []
            pred_map[dep.successor_task_id].append(dep.predecessor_task_id)
        
        # Topological sort and compute times
        computed: Set[str] = set()
        
        def compute_task(task_id: str) -> float:
            if task_id in computed:
                return next(t.early_finish_day for t in tasks if t.id == task_id)
            
            task = next(t for t in tasks if t.id == task_id)
            
            # Compute predecessors first
            max_pred_finish = 0.0
            for pred_id in pred_map.get(task_id, []):
                pred_finish = compute_task(pred_id)
                max_pred_finish = max(max_pred_finish, pred_finish)
            
            task.early_start_day = max_pred_finish
            task.early_finish_day = task.early_start_day + task.duration_days
            computed.add(task_id)
            
            return task.early_finish_day
        
        for task in tasks:
            compute_task(task.id)
    
    def _compute_critical_path(self, plan: PlanOfWork) -> None:
        """Compute critical path and float."""
        if not plan.tasks:
            plan.critical_path_duration_days = 0.0
            return
        
        # Project duration = max early finish
        max_finish = max(t.early_finish_day for t in plan.tasks)
        plan.critical_path_duration_days = max_finish
        
        # Backward pass (late times)
        for task in plan.tasks:
            task.late_finish_day = max_finish
            task.late_start_day = task.late_finish_day - task.duration_days
            task.float_days = task.late_start_day - task.early_start_day
            task.is_critical = abs(task.float_days) < 0.01  # Float ~= 0
        
        # Critical path = tasks with zero float
        plan.critical_path_task_ids = [
            task.id for task in plan.tasks if task.is_critical
        ]
        
        plan.total_float_days = sum(
            max(0, task.float_days or 0) for task in plan.tasks
        )
    
    def _model_to_response(self, model: PlanOfWork) -> PlanResponse:
        """Convert PlanOfWork to response."""
        return PlanResponse(
            plan_artifact_id="",  # Set by caller
            plan_model_id=model.id,
            task_count=model.task_count,
            task_count_by_category=model.task_count_by_category,
            critical_path_duration_days=model.critical_path_duration_days,
            model_hash=model.model_hash or "",
            template_version=model.template_version,
            created_at=model.created_at,
            meta={
                "warnings": model.meta.get("warnings", []),
                "critical_path_tasks": model.critical_path_task_ids,
                "total_float": model.total_float_days,
            },
        )
    
    def register_artifact(
        self,
        cost_model_id: str,
        plan_model: PlanOfWork,
        template_version: str = "1.0.0",
        context: Optional[Any] = None,
    ) -> str:
        """
        Register plan artifact in media_v2.
        
        Returns artifact ID for registered plan model.
        """
        artifact_id = f"plan_{cost_model_id}_{plan_model.model_hash}"
        return artifact_id


# Module-level default service
_default_service: Optional[PlanOfWorkService] = None


def get_plan_service() -> PlanOfWorkService:
    """Get default plan service."""
    global _default_service
    if _default_service is None:
        _default_service = PlanOfWorkService()
    return _default_service


def set_plan_service(service: PlanOfWorkService) -> None:
    """Override default service (for testing)."""
    global _default_service
    _default_service = service
