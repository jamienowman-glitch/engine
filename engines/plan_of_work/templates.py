"""
Task Templates - Template definitions and mapping from BoQ categories.

Implements:
- Task templates per element type
- Duration estimation formulas
- Dependency rules
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.plan_of_work.models import PlanTask, TaskCategory, DependencyType, PlanDependency


class TaskTemplate:
    """Template for generating tasks from BoQ items."""
    
    def __init__(
        self,
        boq_type: str,
        task_name: str,
        task_description: str,
        category: TaskCategory,
        duration_formula: str,  # e.g., "quantity * 0.1" (days per unit)
        resource_tags: Optional[List[str]] = None,
        predecessor_categories: Optional[List[TaskCategory]] = None,
    ):
        self.boq_type = boq_type
        self.task_name = task_name
        self.task_description = task_description
        self.category = category
        self.duration_formula = duration_formula
        self.resource_tags = resource_tags or []
        self.predecessor_categories = predecessor_categories or []
    
    def estimate_duration(self, quantity: float, productivity_rate: float = 1.0) -> float:
        """
        Estimate task duration from quantity and productivity.
        
        Formula: quantity * base_rate / productivity_rate
        """
        # Parse duration formula and evaluate
        # For simplicity, assume formulas like "quantity * 0.1"
        try:
            # Replace 'quantity' with actual value in formula
            formula = self.duration_formula.replace("quantity", str(quantity))
            duration = eval(formula)  # Simple eval for MVP
            return max(1.0, duration / productivity_rate)  # Min 1 day
        except Exception:
            return 1.0  # Default fallback


# Template definitions
TEMPLATES = {
    "wall": TaskTemplate(
        boq_type="wall",
        task_name="Wall framing/construction",
        task_description="Wall layout, framing, and finishes",
        category=TaskCategory.STRUCTURE,
        duration_formula="quantity * 0.05",  # 0.05 days per m²
        resource_tags=["carpenters", "laborers"],
        predecessor_categories=[TaskCategory.FOUNDATION],
    ),
    "slab": TaskTemplate(
        boq_type="slab",
        task_name="Slab pour/construction",
        task_description="Formwork, rebar, and concrete pour",
        category=TaskCategory.STRUCTURE,
        duration_formula="quantity * 0.08",  # 0.08 days per m²
        resource_tags=["concrete_workers", "laborers"],
        predecessor_categories=[TaskCategory.FOUNDATION],
    ),
    "column": TaskTemplate(
        boq_type="column",
        task_name="Column installation",
        task_description="Column setting and bracing",
        category=TaskCategory.STRUCTURE,
        duration_formula="quantity * 0.5",  # 0.5 days per column
        resource_tags=["steel_workers"],
        predecessor_categories=[TaskCategory.FOUNDATION],
    ),
    "door": TaskTemplate(
        boq_type="door",
        task_name="Door installation",
        task_description="Door frames and hardware",
        category=TaskCategory.DOORS_WINDOWS,
        duration_formula="quantity * 0.25",  # 0.25 days per door
        resource_tags=["carpenters"],
        predecessor_categories=[TaskCategory.STRUCTURE, TaskCategory.ENVELOPE],
    ),
    "window": TaskTemplate(
        boq_type="window",
        task_name="Window installation",
        task_description="Window frames and glazing",
        category=TaskCategory.DOORS_WINDOWS,
        duration_formula="quantity * 0.3",  # 0.3 days per window
        resource_tags=["glaziers"],
        predecessor_categories=[TaskCategory.STRUCTURE, TaskCategory.ENVELOPE],
    ),
    "room": TaskTemplate(
        boq_type="room",
        task_name="Room finishing",
        task_description="Flooring, painting, fixtures",
        category=TaskCategory.FINISHES,
        duration_formula="quantity * 0.04",  # 0.04 days per m²
        resource_tags=["finishers", "painters"],
        predecessor_categories=[TaskCategory.MEP, TaskCategory.DOORS_WINDOWS],
    ),
    "stair": TaskTemplate(
        boq_type="stair",
        task_name="Stair construction",
        task_description="Stair assembly and railing",
        category=TaskCategory.STRUCTURE,
        duration_formula="quantity * 3.0",  # 3 days per stair
        resource_tags=["carpenters", "steelworkers"],
        predecessor_categories=[TaskCategory.STRUCTURE],
    ),
    "unknown": TaskTemplate(
        boq_type="unknown",
        task_name="Miscellaneous work",
        task_description="Other construction tasks",
        category=TaskCategory.FINISHES,
        duration_formula="quantity * 0.2",
        resource_tags=["general_labor"],
        predecessor_categories=[],
    ),
}


def get_template(boq_type: str) -> TaskTemplate:
    """Get task template for BoQ type."""
    return TEMPLATES.get(boq_type, TEMPLATES["unknown"])


def get_dependency_order() -> List[TaskCategory]:
    """Get logical order of task categories."""
    return [
        TaskCategory.FOUNDATION,
        TaskCategory.STRUCTURE,
        TaskCategory.ENVELOPE,
        TaskCategory.MEP,
        TaskCategory.DOORS_WINDOWS,
        TaskCategory.FINISHES,
        TaskCategory.TESTING,
        TaskCategory.HANDOVER,
    ]
