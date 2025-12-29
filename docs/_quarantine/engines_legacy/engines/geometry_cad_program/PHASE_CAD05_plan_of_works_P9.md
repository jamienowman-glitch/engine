1. Goal  
Generate plan-of-works (tasks, durations, sequencing) from BoQ/cost semantics.

2. Scope (In / Out)  
- In: task templates per element type, durations derived from quantities, dependencies/DAG, plan export.  
- Out: diffs/risk/portfolio (later phases), UI/auth/tenant/safety.

3. Modules to touch  
- engines/plan_of_work/*  
- engines/plan_of_work/tests/*  
- engines/boq_quantities/models.py (read-only unless fields needed)  
- engines/boq_costing/models.py (read-only unless fields needed)  
- docs/engines/geometry_cad_program/PHASE_CAD05_plan_of_works_P9.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Define PlanTask schema (id, name, predecessors, duration, resource tags, cost ref, level/zone) with deterministic IDs/order; include calendar assumptions.  
- Build task templates per element (wall build, slab pour, door install, window install, MEP placeholders) with duration formulas derived from quantities and productivity rates.  
- Generate DAG: link tasks via dependencies (structural before finishes, level sequencing) and compute critical path duration; detect cycles.  
- Aggregate per-level schedules and overall timeline; include float/slack metadata.  
- Export plan artifact (JSON) with version + meta (productivity assumptions, calendar); optionally register via media_v2.  
- Validate inputs; warn on missing rates/durations; deterministic output for same inputs.  
- Keep BoQ/Cost schemas intact; tag CONTRACT CHANGE if new fields required.

5. Tests  
- engines/plan_of_work/tests: sample BoQ → expected tasks count/dependencies/durations; cycle detection; critical path correctness; determinism.  
- Edge cases: zero-quantity items skipped; missing rates produce warnings not crashes.

6. Docs  
- Update this phase doc with task template table, DAG example, export format, and productivity assumptions.  
- Add sample plan artifact snippet.  
- Note dependency on BoQ/Cost versions in geometry_cad_program docs.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- Keep interfaces stable; if BoQ/Cost fields need to change, mark CONTRACT CHANGE in this doc and update only explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD06 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD05_plan_of_works_P9

1. Goal  
Generate a plan-of-works task graph from costed BoQ data, including dependencies, durations, and critical path for a small real project.

2. North star + Definition of Done  
- North star slice: plan-of-works-lite—given BoQ + cost, produce a deterministic DAG of tasks with durations/resources and a computed critical path for a floorplan-scale project.  
- Definition of Done:  
  - Workers can POST a `boq_cost` artifact and receive a `plan_of_work` artifact (media_v2) containing tasks (id, description, duration, dependencies, resource tags, cost buckets) and project summary (critical path duration, float).  
  - Task templates defined for common categories (structure, envelope, MEP placeholders, finishes) with mapping from BoQ types.  
  - Deterministic task ordering and hash; meta records template_version, source_cost_id.  
  - Tests cover expected task counts/ordering/durations on fixtures and critical path computation; error paths for missing categories handled cleanly.

3. Scope (In / Out)  
- In: task templates, DAG generation, dependency rules, duration estimation from quantities/cost, plan_of_work artifact registration.  
- Out: diffs/risk/portfolio, scheduling UI, auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/plan_of_work/models.py  
- engines/plan_of_work/service.py  
- engines/plan_of_work/routes.py  
- engines/plan_of_work/templates.py (task templates and mapping rules)  
- engines/plan_of_work/tests/test_plan_from_boq.py  
- engines/plan_of_work/tests/test_plan_critical_path.py  
- engines/plan_of_work/tests/test_plan_determinism.py  
- engines/boq_costing/models.py (only if exposing needed fields)  
- engines/boq_costing/tests/* (only if schema changes)  
- engines/media_v2/models.py (only to register plan_of_work artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for plan_of_work artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD05_plan_of_works_P9.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (plan-of-works summary only)  
- READ-ONLY context: diff/risk/portfolio modules and docs not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define/confirm `PlanTask` schema (id, name, description, category, duration_days, dependencies, resource_tags, cost_refs, calc_version).  
  - Register `plan_of_work` artifact kind with meta (task_count, critical_path_days, template_version, hash, source_cost_id).  
- Templates & mapping  
  - Create task templates mapped from BoQ types/categories (e.g., walls → framing tasks; slabs → foundation tasks; openings → install tasks).  
  - Include duration estimation rules based on quantities and productivity rates; allow override of productivity config.  
- DAG generation  
  - Build dependencies (foundation before framing, framing before finishes, etc.); ensure acyclic graph; compute critical path and floats.  
  - Sort tasks deterministically; compute artifact hash.  
- Service & routes  
  - In service.py: load boq_cost artifact, generate PlanTasks via templates + rules, compute critical path, register artifact; support caching by cost_id + template_version + productivity params.  
  - In routes.py: POST /cad/plan_of_work endpoint returning artifact id/meta; validate RequestContext presence only.  
- Validation & errors  
  - Clear errors for missing categories; allow optional placeholders with warnings instead of crashing.  
- Fixtures  
  - Use cost fixtures; expected task counts/durations and critical path documented in tests.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/plan_of_work/tests/test_plan_from_boq.py: generates tasks from BoQ fixture; asserts counts, categories, deterministic ordering/hash.  
- engines/plan_of_work/tests/test_plan_critical_path.py: validates critical path duration and dependencies for fixture; checks float calculations.  
- engines/plan_of_work/tests/test_plan_determinism.py: same input → same graph/hash; cache hit/miss on param changes.  
- engines/media_v2/tests/test_media_v2_endpoints.py: plan_of_work artifact validation and tenant/env enforcement if applicable.

7. Docs & examples  
- Update this phase doc with template mapping table (BoQ category → tasks), productivity assumptions, meta fields.  
- Update lane_B master plan plan-of-works section.  
- Example: POST /cad/boq_cost → cost_id; POST /cad/plan_of_work → tasks + critical path meta.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If PlanTask schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD06 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
