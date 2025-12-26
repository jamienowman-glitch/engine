"""
Timeline Service.

Manages tasks and dependencies with tenant isolation and graph logic.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Set
from collections import deque, defaultdict

from datetime import datetime, timedelta
from engines.timeline_core.models import Task, Dependency, TaskStatus, DependencyType, ContentPlanPayload, GanttItem, GanttRow, GanttView
# Adapters
from engines.plan_of_work.models import PlanOfWork
from engines.boq_quantities.models import BoQModel

class TimelineService:
    """
    Service for managing timeline tasks and dependencies.
    currently in-memory storage.
    """
    
    def __init__(self):
        # Storage: task_id -> Task
        self._tasks: Dict[str, Task] = {}
        # Storage: (from_id, to_id) -> Dependency
        # Also keeping adjacency list for efficient graph algo
        self._deps: List[Dependency] = []
        
    def _validate_context(self, context: Dict[str, Any]) -> tuple[str, str]:
        """Extract and validate tenant/env from context."""
        tenant_id = context.get("tenant_id")
        env = context.get("env")
        if not tenant_id or not env:
            raise ValueError("Context must provide tenant_id and env")
        return tenant_id, env

    def _ensure_task_access(self, task: Task, tenant_id: str, env: str):
        """Ensure task belongs to the requesting tenant/env."""
        if task.tenant_id != tenant_id or task.env != env:
            raise ValueError(f"Access denied to task {task.id}")

    def create_task(self, context: Dict[str, Any], task: Task) -> str:
        """Create a new task."""
        tenant_id, env = self._validate_context(context)
        
        # Enforce context match
        if task.tenant_id != tenant_id or task.env != env:
            raise ValueError("Task tenant/env must match context")
            
        # Check ID collision (though unlikely with uuid)
        if task.id in self._tasks:
            # If same ID exists, ensure it's idempotent if content matches, or conflict?
            # For deterministic IDs, we might want upsert or fail.
            # T01.3 spec says "Create/update/delete". Let's assume fail if exists for create, use update otherwise.
            # Actually, standard REST `create` usually fails if exists.
            # But the deterministic ID requirement suggests we might want to handle re-creation gracefully?
            # Let's enforce uniqueness: if ID exists, raise generic error.
            raise ValueError(f"Task with ID {task.id} already exists")
            
        self._tasks[task.id] = task
        return task.id

    def get_task(self, context: Dict[str, Any], task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        tenant_id, env = self._validate_context(context)
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        # Security: if task exists but belongs to another tenant, treat as Not Found.
        if task.tenant_id != tenant_id or task.env != env:
            return None
            
        return task

    def update_task(self, context: Dict[str, Any], task: Task) -> Task:
        """Update an existing task."""
        tenant_id, env = self._validate_context(context)
        existing = self._tasks.get(task.id)
        if not existing:
            raise ValueError(f"Task {task.id} not found")
        
        self._ensure_task_access(existing, tenant_id, env)
        
        if task.tenant_id != tenant_id or task.env != env:
             raise ValueError("Cannot move task to different tenant/env")
             
        self._tasks[task.id] = task
        return task

    def list_tasks(
        self,
        context: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """
        List tasks matching filters.
        Filters: tags (list), status (enum), group_id (str), lane_id (str)
        """
        tenant_id, env = self._validate_context(context)
        filters = filters or {}
        
        result = []
        for task in self._tasks.values():
            if task.tenant_id != tenant_id or task.env != env:
                continue
                
            # Apply filters
            if "status" in filters and task.status != filters["status"]:
                continue
            if "group_id" in filters and task.group_id != filters["group_id"]:
                continue
            if "lane_id" in filters and task.lane_id != filters["lane_id"]:
                continue
            if "tags" in filters:
                # Require ALL tags? or ANY? Let's say ANY intersection for now, or strict subset?
                # Simplest: if filter has tag "A", task must have "A".
                required_tags = set(filters["tags"])
                task_tags = set(task.tags)
                if not required_tags.issubset(task_tags):
                    continue
            
            result.append(task)
        
        # Determine sorting? Start time default.
        result.sort(key=lambda t: t.start_ts)
        return result

    def add_dependency(self, context: Dict[str, Any], from_id: str, to_id: str) -> None:
        """Add dependency between tasks."""
        tenant_id, env = self._validate_context(context)
        
        # Verify tasks exist and belong to tenant
        t_from = self.get_task(context, from_id)
        t_to = self.get_task(context, to_id)
        
        if not t_from or not t_to:
            raise ValueError("One or both tasks not found")
            
        if from_id == to_id:
            raise ValueError("Cannot depend on self")

        # Check cycle
        # We need to construct graph for this tenant to check
        # Optimization: only check graph reachable from 'to_id' to see if it reaches 'from_id'
        if self._detect_path(context, to_id, from_id):
            raise ValueError(f"Cycle detected: {to_id} -> ... -> {from_id} is already implied, cannot add {from_id}->{to_id}")
            
        # Add dep
        dep = Dependency(from_task_id=from_id, to_task_id=to_id)
        self._deps.append(dep)

    def get_dependencies(self, context: Dict[str, Any]) -> List[Dependency]:
        """Get all dependencies for current scope."""
        tenant_id, env = self._validate_context(context)
        # return deps where both From and To are in this tenant
        # Since we validate on add, checking one should be enough if we trust our state.
        # But for robustness we check if 'from_task' exists in our filtered view.
        
        relevant_deps = []
        for dep in self._deps:
            # Check if one of the tasks is in this tenant.
            # Optimization: since we don't store tenant on Dependency, we look up task.
            t = self._tasks.get(dep.from_task_id)
            if t and t.tenant_id == tenant_id and t.env == env:
                relevant_deps.append(dep)
        
        return relevant_deps

    def _build_adjacency(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Helper to build adjacency list for current tenant."""
        tenant_id, env = self._validate_context(context)
        adj = defaultdict(list)
        
        # Filter deps valid for this tenant
        current_deps = self.get_dependencies(context)
        for dep in current_deps:
            adj[dep.from_task_id].append(dep.to_task_id)
            
        return adj

    def _detect_path(self, context: Dict[str, Any], start_id: str, target_id: str) -> bool:
        """BFS to see if target is reachable from start."""
        adj = self._build_adjacency(context)
        queue = deque([start_id])
        visited = {start_id}
        
        while queue:
            curr = queue.popleft()
            if curr == target_id:
                return True
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def topological_sort(self, context: Dict[str, Any]) -> List[Task]:
        """Return tasks in dependency order."""
        # Kahn's algorithm
        tenant_id, env = self._validate_context(context)
        all_tasks = self.list_tasks(context)
        task_map = {t.id: t for t in all_tasks}
        task_ids = set(task_map.keys())
        
        adj = self._build_adjacency(context)
        in_degree = {bg_id: 0 for bg_id in task_ids}
        
        for u in adj:
            for v in adj[u]:
                if v in in_degree:
                    in_degree[v] += 1
        
        queue = deque([tid for tid in task_ids if in_degree[tid] == 0])
        sorted_tasks = []
        
        while queue:
            u = queue.popleft()
            if u in task_map:
                sorted_tasks.append(task_map[u])
            
            for v in adj[u]:
                if v in in_degree:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)
                        
        if len(sorted_tasks) != len(task_ids):
            # Graph has cycle or mismatch
            raise ValueError("Graph has a cycle, cannot sort")
            
        return sorted_tasks

    def import_from_plan_of_work(
        self,
        context: Dict[str, Any],
        plan: PlanOfWork,
        project_start_ts: datetime
    ) -> List[str]:
        """
        Import tasks from a PlanOfWork.
        Converts relative days to absolute timestamps.
        Idempotent: overwrites existing tasks with same deterministic ID.
        """
        tenant_id, env = self._validate_context(context)
        imported_ids = []
        
        # 1. Tasks
        for p_task in plan.tasks:
            # Deterministic ID
            # Rule: tenant|env|source_kind|source_id
            task_id = Task.generate_deterministic_id(
                tenant_id, env, "plan_task", p_task.id
            )
            
            # Calculate dates
            start_ts = project_start_ts + timedelta(days=p_task.early_start_day)
            duration_ms = p_task.duration_days * 24 * 3600 * 1000
            end_ts = start_ts + timedelta(milliseconds=duration_ms)
            
            t = Task(
                id=task_id,
                tenant_id=tenant_id,
                env=env,
                request_id=f"import_plan_{plan.id}",
                title=p_task.name,
                start_ts=start_ts,
                end_ts=end_ts,
                duration_ms=duration_ms,
                status=TaskStatus.TODO,
                tags=[p_task.category.value] + p_task.resource_tags,
                lane_id=p_task.category.value,
                source_kind="plan_task",
                source_id=p_task.id,
                meta={
                    "description": p_task.description,
                    "original_days": p_task.duration_days,
                    "is_critical": p_task.is_critical,
                    "cost_refs": p_task.cost_refs
                }
            )
            
            # Upsert
            existing = self.get_task(context, task_id)
            if existing:
                self.update_task(context, t)
            else:
                self.create_task(context, t)
            imported_ids.append(task_id)

        # 2. Dependencies
        # Map plan dependency types to timeline dependency types
        # PlanDependency type is string vs string, need mapping if enums differ.
        # Plan: FINISH_TO_START, START_TO_START
        # Timeline: FINISH_TO_START, START_TO_START
        
        # We need to look up the timeline IDs for the plan task IDs.
        # Since deterministic ID is function of plan_task.id + context, we can recompute.
        
        for p_dep in plan.all_dependencies:
            from_tl_id = Task.generate_deterministic_id(tenant_id, env, "plan_task", p_dep.predecessor_task_id)
            to_tl_id = Task.generate_deterministic_id(tenant_id, env, "plan_task", p_dep.successor_task_id)
            
            try:
                # Upsert dependency?
                # Service only has add_dependency. 
                # Check if exists first to avoid double add or cycle error if re-running?
                # For naive MVP, try add, catch if exists/cycle?
                # Actually, duplicate deps are fine in list? Logic says "self._deps.append".
                # To be idempotent, we should check if dep exists.
                exists = any(
                    d.from_task_id == from_tl_id and d.to_task_id == to_tl_id 
                    for d in self._deps
                )
                if not exists:
                    self.add_dependency(context, from_tl_id, to_tl_id)
            except ValueError:
                # Ignore cycles if they existed in plan (shouldn't happen if plan is valid DAG)
                pass
                
        return imported_ids

    def import_from_boq(
        self,
        context: Dict[str, Any],
        boq: BoQModel,
        project_start_ts: datetime
    ) -> List[str]:
        """
        Import tasks from BoQModel.
        Creates backlog items (1 hr duration default) grouped by Scope/Element.
        """
        tenant_id, env = self._validate_context(context)
        imported_ids = []
        
        # Helper for scope names
        scope_map = {s.scope_id: s.scope_name for s in boq.scopes}
        
        for item in boq.items:
            task_id = Task.generate_deterministic_id(
                tenant_id, env, "boq_item", item.id
            )
            
            # Default scheduling: placeholder
            start_ts = project_start_ts
            duration_ms = 3600 * 1000 # 1 hour
            end_ts = start_ts + timedelta(milliseconds=duration_ms)
            
            group_name = scope_map.get(item.scope_id, "Unscoped")
            
            t = Task(
                id=task_id,
                tenant_id=tenant_id,
                env=env,
                request_id=f"import_boq_{boq.id}",
                title=f"{item.element_type} - {item.quantity} {item.unit.value}",
                start_ts=start_ts,
                end_ts=end_ts,
                duration_ms=duration_ms,
                status=TaskStatus.TODO,
                tags=[item.element_type],
                group_id=group_name,
                lane_id=item.element_type, # Trade/Element
                source_kind="boq_item",
                source_id=item.id,
                meta={
                    "quantity": item.quantity,
                    "unit": item.unit.value,
                    "scope_id": item.scope_id
                }
            )
            
            existing = self.get_task(context, task_id)
            if existing:
                self.update_task(context, t)
            else:
                self.create_task(context, t)
            imported_ids.append(task_id)
            
        return imported_ids

    def import_from_content_plan(
        self,
        context: Dict[str, Any],
        plan: ContentPlanPayload
    ) -> List[str]:
        """
        Import tasks from ContentPlanPayload.
        Tasks are created with start_ts = end_ts = due_date (milestone-like).
        """
        tenant_id, env = self._validate_context(context)
        imported_ids = []
        
        for item in plan.items:
            task_id = Task.generate_deterministic_id(
                tenant_id, env, "content_item", item.id
            )
            
            # Using point-in-time for due date
            start_ts = item.due_date
            end_ts = item.due_date
            
            # Combine tags
            tags = item.tags.copy()
            if item.owner:
                tags.append(f"owner:{item.owner}")
            
            t = Task(
                id=task_id,
                tenant_id=tenant_id,
                env=env,
                request_id=f"import_content_{task_id}", 
                title=f"{item.campaign} - {item.asset} ({item.channel})",
                start_ts=start_ts,
                end_ts=end_ts,
                duration_ms=0, # Milestone
                status=TaskStatus.TODO,
                tags=tags,
                group_id=item.campaign,
                lane_id=item.channel,
                source_kind="content_item",
                source_id=item.id,
                meta={
                    "campaign": item.campaign,
                    "asset": item.asset,
                    "owner": item.owner,
                    "visuals": {
                        "icon": self._map_channel_icon(item.channel),
                        "color": self._map_campaign_color(item.campaign),
                        "tooltip": {
                            "Campaign": item.campaign,
                            "Asset": item.asset,
                            "Owner": item.owner or "Unassigned"
                        }
                    }
                }
            )
            
            existing = self.get_task(context, task_id)
            if existing:
                self.update_task(context, t)
            else:
                self.create_task(context, t)
            imported_ids.append(task_id)
            
        return imported_ids

    def get_gantt_view(
        self,
        context: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> GanttView:
        """
        Generate a GanttView from current tasks.
        Hierarchy: Group -> Lane -> Items.
        """
        tenant_id, env = self._validate_context(context)
        tasks = self.list_tasks(context, filters)
        
        # Build dependency map (predecessors for each task)
        # We need ALL dependencies for these tasks, even if the other task is filtered out?
        # Usually Gantt shows lines to visible predecessors. 
        # So we filter deps where both ends are in `tasks`.
        task_ids = set(t.id for t in tasks)
        deps = self.get_dependencies(context)
        
        predecessors = defaultdict(list)
        for d in deps:
            if d.to_task_id in task_ids and d.from_task_id in task_ids:
                predecessors[d.to_task_id].append(d.from_task_id)

        # Organization
        # structure: { group_id: { lane_id: [items] } }
        grouped = defaultdict(lambda: defaultdict(list))
        unscoped = []
        
        min_ts = None
        max_ts = None
        
        for t in tasks:
            # Update bounds
            if t.start_ts:
                if min_ts is None or t.start_ts < min_ts:
                    min_ts = t.start_ts
                if max_ts is None or t.start_ts > max_ts:
                    max_ts = t.start_ts
                    
            if t.end_ts:
                end = t.end_ts
            elif t.duration_ms:
                end = t.start_ts + timedelta(milliseconds=t.duration_ms)
            else:
                end = t.start_ts
                
            if max_ts is None or end > max_ts:
                max_ts = end
            
            # Create View Item
            vis = t.meta.get("visuals", {})
            item = GanttItem(
                id=t.id,
                label=t.title,
                start=t.start_ts,
                end=end,
                status=t.status,
                dependencies=predecessors[t.id],
                color=vis.get("color"),
                progress=vis.get("progress", 0.0),
                icon=vis.get("icon"),
                tooltip=vis.get("tooltip", {}),
                meta=t.meta
            )
            
            if t.group_id:
                lane = t.lane_id or "Default"
                grouped[t.group_id][lane].append(item)
            else:
                unscoped.append(item)
                
        # Build Rows
        rows = []
        for group_id, lanes in grouped.items():
            # Create sub-rows for lanes
            sub_rows = []
            for lane_id, items in lanes.items():
                # Sort items by start time
                items.sort(key=lambda x: x.start)
                sub_rows.append(GanttRow(
                    id=lane_id,
                    label=lane_id,
                    items=items
                ))
            
            # Sort sub-rows by label?
            sub_rows.sort(key=lambda x: x.label)
            
            # The group row itself might carry items if they have group but no lane? 
            # Our logic put them in "Default" lane.
            
            rows.append(GanttRow(
                id=group_id,
                label=group_id,
                sub_rows=sub_rows
            ))
            
        # Sort rows by label
        rows.sort(key=lambda x: x.label)
        
        return GanttView(
            project_start=min_ts,
            project_end=max_ts,
            rows=rows,
            unscoped_items=unscoped
        )

    def _map_channel_icon(self, channel: str) -> str:
        """Map channel to icon key."""
        icons = {
            "YouTube": "youtube",
            "Instagram": "instagram",
            "TikTok": "tiktok",
            "Blog": "file-text",
            "Email": "mail"
        }
        return icons.get(channel, "hash")

    def _map_campaign_color(self, campaign: str) -> str:
        """Map campaign string to deterministic color."""
        # Simple hash to color
        hash_val = hashlib.sha256(campaign.encode()).hexdigest()
        # Take first 6 chars as hex color, ensure it's valid
        color = f"#{hash_val[:6]}"
        return color

    def _map_trade_color(self, trade: str) -> str:
        """Map trade to pastel color."""
        # Simple deterministic mapping or fixed palette
        palette = {
            "Plumbing": "#ADD8E6", # LightBlue
            "Electrical": "#FFFFE0", # LightYellow
            "Structural": "#FFB6C1", # LightPink
            "HVAC": "#98FB98", # PaleGreen
            "Fitout": "#E6E6FA"  # Lavender
        }
        return palette.get(trade, "#D3D3D3") # LightGray default
