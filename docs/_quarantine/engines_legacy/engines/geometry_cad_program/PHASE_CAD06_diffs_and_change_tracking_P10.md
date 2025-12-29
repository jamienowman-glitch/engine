1. Goal  
Compute diffs between CAD versions and map impacts to BoQ/Cost/Plan.

2. Scope (In / Out)  
- In: geometry/semantic diffing, BoQ/Cost/Plan delta computation and impact tagging.  
- Out: risk/scenario (next phase), UI/auth/tenant/safety.

3. Modules to touch  
- engines/cad_diff/*  
- engines/cad_diff/tests/*  
- engines/cad_semantics/models.py (read-only unless IDs/schema change)  
- engines/boq_quantities/models.py (read-only unless impacted)  
- engines/boq_costing/models.py (read-only unless impacted)  
- engines/plan_of_work/models.py (read-only unless impacted)  
- docs/engines/geometry_cad_program/PHASE_CAD06_diffs_and_change_tracking_P10.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Implement diff on semantic elements with stable IDs: added/removed/changed attributes/geometry; classify change types (move/resize/type-change).  
- Propagate impacts: for changed elements recompute quantities/costs/tasks and flag deltas; include references to affected BoQ items and plan tasks.  
- Produce delta artifacts (summary + per-entity) with deterministic ordering and version meta.  
- Handle rename-only vs geometry change distinctly; ignore cosmetic layer renames if no geometry change.  
- Provide clear output format (JSON) with counts, impacted costs, schedule adjustments; optionally register via media_v2.  
- Validate inputs (matching schemas/versions) and fail with actionable errors if incompatible; maintain backward compatibility of IDs.  
- Tag CONTRACT CHANGE if semantic IDs/schema must change.

5. Tests  
- engines/cad_diff/tests: two CAD samples (add door, move wall) → expected diff, BoQ delta, cost delta, plan adjustment markers.  
- Edge cases: rename-only vs geometry change; deleted elements; unchanged files produce empty diff.  
- Determinism: same inputs produce identical diff ordering.

6. Docs  
- Update this phase doc with diff format, impact mapping rules, and examples.  
- Add sample delta JSON showing BoQ/Cost/Plan impacts.  
- Note schema/version compatibility requirements.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- Keep IDs stable; tag CONTRACT CHANGE if semantics IDs change and update dependent modules only.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD07 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD06_diffs_and_change_tracking_P10

1. Goal  
Compute diffs between CAD versions and propagate impacts to BoQ, cost, and plan-of-works artifacts with deterministic reporting.

2. North star + Definition of Done  
- North star slice: change-tracking-lite—given two cad_model/semantics/BoQ/cost/plan artifacts, produce a `cad_diff` artifact summarizing adds/removes/modifications and impact on quantities, costs, and tasks.  
- Definition of Done:  
  - Workers can POST a pair of artifact IDs (old/new cad_semantics or BoQ/cost/plan) and get a `cad_diff` artifact (media_v2) listing element-level changes, BoQ deltas, cost deltas, and affected tasks with severity tags.  
  - Diffing uses stable IDs; includes summary stats and hash; deterministic ordering.  
  - Tests cover element-level diffs, BoQ/cost deltas, task impact propagation, and determinism on fixtures with known edits.

3. Scope (In / Out)  
- In: diff models, diff service/routes, impact calculation to BoQ/cost/plan, artifact registration.  
- Out: risk scoring (next phase), portfolio, UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/cad_diff/models.py  
- engines/cad_diff/service.py  
- engines/cad_diff/routes.py  
- engines/cad_diff/tests/test_diff_semantics.py  
- engines/cad_diff/tests/test_diff_boq_cost_plan.py  
- engines/cad_diff/tests/test_diff_determinism.py  
- engines/cad_semantics/models.py (READ-ONLY unless schema change marked CONTRACT CHANGE)  
- engines/boq_quantities/models.py (READ-ONLY unless schema change marked)  
- engines/boq_costing/models.py (READ-ONLY unless schema change marked)  
- engines/plan_of_work/models.py (READ-ONLY unless schema change marked)  
- engines/media_v2/models.py (only to register cad_diff artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for cad_diff artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD06_diffs_and_change_tracking_P10.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (diffs summary only)  
- READ-ONLY context: risk/portfolio modules and docs not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define `CadDiff` schema (added/removed/modified elements, BoQ deltas, cost deltas, impacted tasks, severity levels, hash, calc_version).  
  - Register `cad_diff` artifact kind with meta (source_artifact_ids, stats, hash).  
- Diff logic  
  - Element-level diff: compare SemanticElements by stable id; classify add/remove/modify; record attribute changes.  
  - BoQ/cost diff: compute deltas per type/category; record currency context.  
  - Plan impact: map changed elements/BoQ items to tasks via cost/plan references; flag impacted tasks.  
- Service & routes  
  - In service.py: accept artifact pair (semantics or BoQ or cost or plan), run diff pipeline, register cad_diff artifact; support caching by input ids + calc_version.  
  - In routes.py: POST /cad/diff endpoint accepting old/new ids and target stage; return artifact id/meta; validate RequestContext presence only.  
- Determinism & ordering  
  - Sort diff entries deterministically; compute hash; ensure repeatable output for same inputs.  
- Validation & errors  
  - Validate inputs are compatible stages; clear errors if mismatched or missing artifacts.  
- Fixtures  
  - Add edited fixture (e.g., door added, wall moved) to test diffs; expected deltas documented.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/cad_diff/tests/test_diff_semantics.py: element-level adds/removes/modifications on fixture; determinism/hash.  
- engines/cad_diff/tests/test_diff_boq_cost_plan.py: BoQ and cost deltas; impacted PlanTasks flagged; currency preserved.  
- engines/cad_diff/tests/test_diff_determinism.py: same inputs → same diff; cache hit/miss with calc_version changes.  
- engines/media_v2/tests/test_media_v2_endpoints.py: cad_diff artifact validation and tenant/env enforcement if applicable.  
- Negative tests: incompatible stage inputs rejected with clear error.

7. Docs & examples  
- Update this phase doc with diff schema, severity definitions, meta fields.  
- Update lane_B master plan diff section.  
- Example: Run ingest/semantics/BoQ/cost/plan for v1 and v2; POST /cad/diff with plan artifacts → diff showing added doors and impacted tasks.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD07 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
