"""
CAD Diff Service - Compute diffs and impact analysis.

Compares artifact versions at multiple stages:
- Semantics: Element-level differences
- BoQ: Quantity changes and cost impact
- Plan: Task schedule and criticality impact
"""

import hashlib
from functools import lru_cache
from typing import Any, Dict, List, Optional

from engines.media_v2.models import DerivedArtifact
from engines.cad_semantics.models import SemanticElement, SpatialGraph, SemanticModel
from engines.boq_quantities.models import BoQItem, BoQModel
from engines.boq_costing.models import CostItem, CostModel
from engines.plan_of_work.models import PlanTask, PlanOfWork

from .models import (
    ChangeType,
    SeverityLevel,
    ElementDiff,
    BoQDelta,
    CostDelta,
    TaskImpact,
    CadDiff,
)


class DiffService:
    """Service for computing diffs between artifact versions."""
    
    CALC_VERSION = "1.0.0"
    
    @staticmethod
    def _cache_key(old_id: str, new_id: str, calc_ver: str) -> str:
        """Generate deterministic cache key."""
        params = f"{old_id}|{new_id}|{calc_ver}".encode("utf-8")
        return hashlib.sha256(params).hexdigest()[:16]
    
    @staticmethod
    def _compute_hash(diff: CadDiff) -> str:
        """Compute deterministic hash of diff content."""
        content = (
            f"{diff.old_artifact_id}|{diff.new_artifact_id}|"
            f"{diff.added_count}|{diff.removed_count}|{diff.modified_count}|"
            f"{diff.total_changes}|{diff.critical_change_count}|{diff.max_severity}"
        ).encode("utf-8")
        return hashlib.sha256(content).hexdigest()[:16]
    
    @staticmethod
    def _sort_diffs(diffs: List[ElementDiff]) -> List[ElementDiff]:
        """Sort element diffs deterministically."""
        return sorted(diffs, key=lambda d: (d.change_type.value, d.element_id))
    
    @staticmethod
    def _sort_boq_deltas(deltas: List[BoQDelta]) -> List[BoQDelta]:
        """Sort BoQ deltas deterministically."""
        return sorted(deltas, key=lambda d: d.boq_item_id)
    
    @staticmethod
    def _sort_cost_deltas(deltas: List[CostDelta]) -> List[CostDelta]:
        """Sort cost deltas deterministically."""
        return sorted(deltas, key=lambda d: d.cost_item_id)
    
    @staticmethod
    def _sort_task_impacts(impacts: List[TaskImpact]) -> List[TaskImpact]:
        """Sort task impacts deterministically."""
        return sorted(impacts, key=lambda t: t.task_id)
    
    @staticmethod
    def _assess_severity_for_element(old_attrs: Dict[str, Any], new_attrs: Dict[str, Any], element_type: str) -> SeverityLevel:
        """Assess severity of element change."""
        # Geometry changes are critical for structural elements
        if element_type in ["structural_wall", "column", "footing"]:
            if old_attrs.get("area") != new_attrs.get("area"):
                return SeverityLevel.CRITICAL
            if old_attrs.get("height") != new_attrs.get("height"):
                return SeverityLevel.CRITICAL
        
        # Non-structural walls and slabs: high severity
        if element_type in ["wall", "slab", "beam"]:
            if old_attrs.get("area") != new_attrs.get("area"):
                return SeverityLevel.HIGH
        
        # Openings: medium severity
        if element_type in ["door", "window", "opening"]:
            if old_attrs.get("area") != new_attrs.get("area"):
                return SeverityLevel.MEDIUM
        
        # Default: low severity
        return SeverityLevel.LOW
    
    @staticmethod
    def _assess_severity_for_boq(old_qty: float, new_qty: float) -> SeverityLevel:
        """Assess severity of quantity change."""
        if old_qty == 0:
            return SeverityLevel.HIGH if new_qty > 0 else SeverityLevel.NONE
        
        pct_change = abs(new_qty - old_qty) / old_qty * 100
        
        if pct_change > 20:
            return SeverityLevel.HIGH
        elif pct_change > 10:
            return SeverityLevel.MEDIUM
        elif pct_change > 0:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.NONE
    
    @staticmethod
    def _assess_severity_for_task(old_days: float, new_days: float, critical: bool) -> SeverityLevel:
        """Assess severity of task impact."""
        if critical:
            return SeverityLevel.CRITICAL if old_days != new_days else SeverityLevel.HIGH
        
        if old_days == 0:
            return SeverityLevel.MEDIUM if new_days > 0 else SeverityLevel.NONE
        
        pct_change = abs(new_days - old_days) / old_days * 100
        
        if pct_change > 20:
            return SeverityLevel.HIGH
        elif pct_change > 10:
            return SeverityLevel.MEDIUM
        elif pct_change > 0:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.NONE
    
    @classmethod
    def diff_semantics(
        cls,
        old_semantics: SemanticModel,
        new_semantics: SemanticModel,
    ) -> CadDiff:
        """
        Compute semantic element-level diff.
        
        Args:
            old_semantics: Old semantic artifact
            new_semantics: New semantic artifact
        
        Returns:
            CadDiff with element-level changes
        """
        element_diffs: List[ElementDiff] = []
        
        # Index old and new elements by ID
        old_elements = {e.id: e for e in old_semantics.elements}
        new_elements = {e.id: e for e in new_semantics.elements}
        
        # Detect added and removed
        old_ids = set(old_elements.keys())
        new_ids = set(new_elements.keys())
        
        added_ids = new_ids - old_ids
        removed_ids = old_ids - new_ids
        common_ids = old_ids & new_ids
        
        # Added elements
        for elem_id in sorted(added_ids):
            elem = new_elements[elem_id]
            severity = SeverityLevel.MEDIUM
            diff = ElementDiff(
                element_id=elem_id,
                element_type=elem.semantic_type,
                change_type=ChangeType.ADDED,
                new_attributes=elem.model_dump(exclude={"id", "semantic_type"}),
                severity=severity,
                impact_tags=["cost_impact", "schedule_impact"],
            )
            element_diffs.append(diff)
        
        # Removed elements
        for elem_id in sorted(removed_ids):
            elem = old_elements[elem_id]
            severity = SeverityLevel.MEDIUM
            diff = ElementDiff(
                element_id=elem_id,
                element_type=elem.semantic_type,
                change_type=ChangeType.REMOVED,
                old_attributes=elem.model_dump(exclude={"id", "semantic_type"}),
                severity=severity,
                impact_tags=["cost_impact", "schedule_impact"],
            )
            element_diffs.append(diff)
        
        # Modified elements
        for elem_id in sorted(common_ids):
            old_elem = old_elements[elem_id]
            new_elem = new_elements[elem_id]
            
            old_attrs = old_elem.model_dump(exclude={"id", "semantic_type", "created_at"})
            new_attrs = new_elem.model_dump(exclude={"id", "semantic_type", "created_at"})
            
            if old_attrs != new_attrs:
                # Detect attribute changes
                attr_changes = {}
                for key in set(old_attrs.keys()) | set(new_attrs.keys()):
                    if old_attrs.get(key) != new_attrs.get(key):
                        attr_changes[key] = (old_attrs.get(key), new_attrs.get(key))
                
                # Assess severity
                severity = cls._assess_severity_for_element(old_attrs, new_attrs, old_elem.semantic_type)
                
                # Check for geometry change
                geometry_changed = any(k in ["area", "height", "width", "length"] for k in attr_changes.keys())
                
                diff = ElementDiff(
                    element_id=elem_id,
                    element_type=old_elem.semantic_type,
                    change_type=ChangeType.MODIFIED,
                    old_attributes=old_attrs,
                    new_attributes=new_attrs,
                    attribute_changes=attr_changes,
                    geometry_changed=geometry_changed,
                    severity=severity,
                    impact_tags=["cost_impact"] if geometry_changed else [],
                )
                element_diffs.append(diff)
        
        # Sort deterministically
        element_diffs = cls._sort_diffs(element_diffs)
        
        # Count changes
        added_count = len([d for d in element_diffs if d.change_type == ChangeType.ADDED])
        removed_count = len([d for d in element_diffs if d.change_type == ChangeType.REMOVED])
        modified_count = len([d for d in element_diffs if d.change_type == ChangeType.MODIFIED])
        total_changes = added_count + removed_count + modified_count
        
        # Count critical changes
        critical_count = len([d for d in element_diffs if d.severity == SeverityLevel.CRITICAL])
        
        # Max severity
        severities = [d.severity for d in element_diffs] if element_diffs else [SeverityLevel.NONE]
        severity_order = {SeverityLevel.CRITICAL: 4, SeverityLevel.HIGH: 3, SeverityLevel.MEDIUM: 2, SeverityLevel.LOW: 1, SeverityLevel.NONE: 0}
        max_severity = max(severities, key=lambda s: severity_order.get(s, 0))
        
        # Build diff
        diff = CadDiff(
            old_artifact_id=old_semantics.id,
            old_artifact_type="cad_semantics",
            new_artifact_id=new_semantics.id,
            new_artifact_type="cad_semantics",
            element_diffs=element_diffs,
            added_count=added_count,
            removed_count=removed_count,
            modified_count=modified_count,
            total_changes=total_changes,
            critical_change_count=critical_count,
            max_severity=max_severity,
            calc_version=cls.CALC_VERSION,
        )
        
        # Compute hash
        diff.model_hash = cls._compute_hash(diff)
        
        return diff
    
    @classmethod
    def diff_boq(
        cls,
        old_boq: BoQModel,
        new_boq: BoQModel,
        old_cost: Optional[CostModel] = None,
        new_cost: Optional[CostModel] = None,
    ) -> CadDiff:
        """
        Compute BoQ quantity and cost diff.
        
        Args:
            old_boq: Old quantities artifact
            new_boq: New quantities artifact
            old_cost: Old costing artifact (optional for cost deltas)
            new_cost: New costing artifact (optional for cost deltas)
        
        Returns:
            CadDiff with BoQ and cost deltas
        """
        boq_deltas: List[BoQDelta] = []
        cost_deltas: List[CostDelta] = []
        
        # Index items by ID
        old_items = {item.id: item for item in old_boq.items}
        new_items = {item.id: item for item in new_boq.items}
        
        old_ids = set(old_items.keys())
        new_ids = set(new_items.keys())
        common_ids = old_ids & new_ids
        
        # Compute BoQ deltas for common items
        for item_id in sorted(common_ids):
            old_item = old_items[item_id]
            new_item = new_items[item_id]
            
            if old_item.quantity != new_item.quantity:
                qty_delta = new_item.quantity - old_item.quantity
                severity = cls._assess_severity_for_boq(old_item.quantity, new_item.quantity)
                
                delta = BoQDelta(
                    boq_item_id=item_id,
                    boq_item_type=old_item.element_type,
                    old_quantity=old_item.quantity,
                    new_quantity=new_item.quantity,
                    quantity_delta=qty_delta,
                    unit=str(old_item.unit),
                    scope_id=old_item.scope_id,
                    severity=severity,
                )
                boq_deltas.append(delta)
        
        # Compute cost deltas if cost artifacts provided
        if old_cost and new_cost:
            old_cost_items = {item.id: item for item in old_cost.items}
            new_cost_items = {item.id: item for item in new_cost.items}
            
            for item_id in sorted(common_ids):
                if item_id in old_cost_items and item_id in new_cost_items:
                    old_ci = old_cost_items[item_id]
                    new_ci = new_cost_items[item_id]
                    
                    if old_ci.total_cost != new_ci.total_cost:
                        cost_delta = new_ci.total_cost - old_ci.total_cost
                        severity = SeverityLevel.HIGH if abs(cost_delta) > 1000 else SeverityLevel.MEDIUM if abs(cost_delta) > 100 else SeverityLevel.LOW
                        
                        cd = CostDelta(
                            cost_item_id=old_ci.id,
                            boq_item_id=item_id,
                            old_cost=old_ci.total_cost,
                            new_cost=new_ci.total_cost,
                            cost_delta=cost_delta,
                            currency=old_ci.currency,
                            severity=severity,
                            affected_by_boq_ids=[item_id],
                        )
                        cost_deltas.append(cd)
        
        # Sort deterministically
        boq_deltas = cls._sort_boq_deltas(boq_deltas)
        cost_deltas = cls._sort_cost_deltas(cost_deltas)
        
        # Statistics
        total_changes = len(boq_deltas) + len(cost_deltas)
        critical_count = len([d for d in boq_deltas if d.severity == SeverityLevel.CRITICAL])
        critical_count += len([d for d in cost_deltas if d.severity == SeverityLevel.CRITICAL])
        
        severities = [d.severity for d in boq_deltas] + [d.severity for d in cost_deltas]
        severities = severities or [SeverityLevel.NONE]
        severity_order = {SeverityLevel.CRITICAL: 4, SeverityLevel.HIGH: 3, SeverityLevel.MEDIUM: 2, SeverityLevel.LOW: 1, SeverityLevel.NONE: 0}
        max_severity = max(severities, key=lambda s: severity_order.get(s, 0))
        
        # Build diff
        diff = CadDiff(
            old_artifact_id=old_boq.id,
            old_artifact_type="boq_quantities",
            new_artifact_id=new_boq.id,
            new_artifact_type="boq_quantities",
            boq_deltas=boq_deltas,
            cost_deltas=cost_deltas,
            total_changes=total_changes,
            critical_change_count=critical_count,
            max_severity=max_severity,
            calc_version=cls.CALC_VERSION,
        )
        
        diff.model_hash = cls._compute_hash(diff)
        return diff
    
    @classmethod
    def diff_plan(
        cls,
        old_plan: PlanOfWork,
        new_plan: PlanOfWork,
    ) -> CadDiff:
        """
        Compute plan-of-works diff with task impact analysis.
        
        Args:
            old_plan: Old plan artifact
            new_plan: New plan artifact
        
        Returns:
            CadDiff with task impacts
        """
        task_impacts: List[TaskImpact] = []
        
        # Index tasks by ID
        old_tasks = {task.id: task for task in old_plan.tasks}
        new_tasks = {task.id: task for task in new_plan.tasks}
        
        common_ids = set(old_tasks.keys()) & set(new_tasks.keys())
        
        # Compute task impacts for common tasks
        for task_id in sorted(common_ids):
            old_task = old_tasks[task_id]
            new_task = new_tasks[task_id]
            
            duration_delta = new_task.duration_days - old_task.duration_days
            critical_changed = old_task.is_critical != new_task.is_critical
            
            if duration_delta != 0 or critical_changed:
                severity = cls._assess_severity_for_task(
                    old_task.duration_days,
                    new_task.duration_days,
                    new_task.is_critical
                )
                
                impact = TaskImpact(
                    task_id=task_id,
                    task_name=old_task.name,
                    old_duration_days=old_task.duration_days,
                    new_duration_days=new_task.duration_days,
                    duration_delta_days=duration_delta,
                    critical_path_impact=critical_changed,
                    old_critical=old_task.is_critical,
                    new_critical=new_task.is_critical,
                    severity=severity,
                )
                task_impacts.append(impact)
        
        # Sort deterministically
        task_impacts = cls._sort_task_impacts(task_impacts)
        
        # Statistics
        critical_impact_count = len([t for t in task_impacts if t.critical_path_impact])
        critical_count = len([t for t in task_impacts if t.severity == SeverityLevel.CRITICAL])
        
        severities = [t.severity for t in task_impacts] or [SeverityLevel.NONE]
        severity_order = {SeverityLevel.CRITICAL: 4, SeverityLevel.HIGH: 3, SeverityLevel.MEDIUM: 2, SeverityLevel.LOW: 1, SeverityLevel.NONE: 0}
        max_severity = max(severities, key=lambda s: severity_order.get(s, 0))
        
        # Build diff
        diff = CadDiff(
            old_artifact_id=old_plan.id,
            old_artifact_type="plan_of_work",
            new_artifact_id=new_plan.id,
            new_artifact_type="plan_of_work",
            task_impacts=task_impacts,
            total_changes=len(task_impacts),
            critical_change_count=critical_count,
            max_severity=max_severity,
            meta={"critical_path_impacts": critical_impact_count},
            calc_version=cls.CALC_VERSION,
        )
        
        diff.model_hash = cls._compute_hash(diff)
        return diff
