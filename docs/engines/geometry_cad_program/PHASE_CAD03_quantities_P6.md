1. Goal  
Extract BoQ quantities from the semantic model with correct units and scope tagging.

2. Scope (In / Out)  
- In: quantity rules per element type, unit conversions, scope tagging per level/zone, aggregation.  
- Out: costing/pricing (next phase), UI/auth/tenant/safety.

3. Modules to touch  
- engines/boq_quantities/*  
- engines/boq_quantities/tests/*  
- engines/cad_semantics/models.py (read-only context unless fields required)  
- engines/cad_semantics/tests/* (only if schema changes)  
- docs/engines/geometry_cad_program/PHASE_CAD03_quantities_P6.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Define BoQItem schema (id, element_type, quantity, unit, location/level/zone, source refs, scope id) with deterministic IDs/order.  
- Implement quantity calculators per element type: wall area/length with opening deductions, slab volume, roof area, door/window counts, column volume/length; handle missing thickness defaults safely.  
- Unit conversions (mm/m/ft) and rounding rules; include original units in meta.  
- Scope tagging: per level/zone with aggregation summaries; include totals per type and per level.  
- Validate inputs from cad_semantics; skip/flag elements with insufficient data; record warnings.  
- Ensure deterministic output ordering and hashing for repeatability.  
- Keep semantic schema compatibility; tag CONTRACT CHANGE if field additions required.

5. Tests  
- engines/boq_quantities/tests: sample CAD fixture → expected quantities (walls with openings deducted, counts, volumes); edge cases (slanted walls, missing thickness, zero-area elements).  
- Determinism test: same input yields identical BoQ list/order.  
- Error-path tests: handles missing semantics gracefully with warnings.

6. Docs  
- Update this phase doc with quantity rules table and examples per element type, including unit/rounding policies.  
- Add sample BoQ JSON snippet with scopes/levels.  
- Note dependency on cad_semantics schema versions.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- Keep interfaces stable; if semantic schema changes, mark CONTRACT CHANGE in this doc and update only explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD04 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD03_quantities_P6

1. Goal  
Compute deterministic BoQ quantities (areas/volumes/lengths/counts) from semantic CAD models and emit BoQ items ready for costing.

2. North star + Definition of Done  
- North star slice: BoQ extraction akin to a lightweight QS tool—given `cad_semantics`, produce a reproducible list of BoQ items with scoped quantities for walls/doors/windows/slabs/finishes.  
- Definition of Done:  
  - Workers can POST a `cad_semantics` artifact and receive a `boq_quantities` artifact (media_v2) containing normalized `BoQItem`s (type, scope, quantity, unit, source_ids, calc_version).  
  - Quantity formulas applied for at least: walls (area/length), slabs (area/volume), windows/doors (count/opening area), columns (count/volume), rooms (area/perimeter).  
  - Deterministic ordering and hash of BoQ items; meta records calc_version, source_semantics_id, tolerances used.  
  - Tests verify expected numbers on fixtures and deterministic results across runs; error paths for missing semantics or unsupported types handled cleanly.

3. Scope (In / Out)  
- In: quantity formulas, BoQ item schema, scope tagging, artifact registration for `boq_quantities`, service/routes to generate quantities.  
- Out: costing, plan-of-works, diffs/risk/portfolio, UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/boq_quantities/models.py  
- engines/boq_quantities/service.py  
- engines/boq_quantities/routes.py  
- engines/boq_quantities/formulas.py  
- engines/boq_quantities/tests/test_quantities_dxf.py  
- engines/boq_quantities/tests/test_quantities_ifc_lite.py  
- engines/boq_quantities/tests/test_quantities_determinism.py  
- engines/cad_semantics/models.py (only if exposing additional fields)  
- engines/cad_semantics/tests/* (only if schema changes)  
- engines/media_v2/models.py (only to register boq_quantities artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for boq_quantities artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD03_quantities_P6.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (quantities summary only)  
- READ-ONLY context: costing/plan/diff/risk/portfolio modules and docs not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define/confirm `BoQItem` schema (id, type, quantity, unit, scope tags, source_element_ids, formula_used, calc_version, meta).  
  - Register `boq_quantities` artifact kind with meta (calc_version, counts by type, hash, source_semantics_id).  
- Formulas  
  - Implement formulas for walls (length, surface area from height), slabs (area, volume from thickness), openings (count/area), columns (count/volume), rooms (area/perimeter).  
  - Include tolerances and snap rules; record applied formula + tolerance in each item.  
- Service & routes  
  - In service.py: load cad_semantics artifact, run formulas, aggregate BoQ items, dedupe by identical scope, register artifact; support caching by semantics_id + calc_version + tolerance params.  
  - In routes.py: POST /cad/boq_quantities endpoint returning artifact id/meta; validate RequestContext presence only.  
- Determinism & ordering  
  - Ensure BoQ items sorted by type then stable id; compute artifact hash for determinism checks.  
- Validation & errors  
  - Clear errors for missing semantic types; skip/flag unsupported types without crashing.  
- Fixtures  
  - Use semantics fixtures; add expected quantities per fixture in tests; include hash assertions.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/boq_quantities/tests/test_quantities_dxf.py: expected quantities for DXF fixture, ordering, hash determinism, cache hit/miss on param changes.  
- engines/boq_quantities/tests/test_quantities_ifc_lite.py: same for IFC-lite fixture.  
- engines/boq_quantities/tests/test_quantities_determinism.py: same input → same BoQ list/hash; tolerance edge cases.  
- engines/media_v2/tests/test_media_v2_endpoints.py: boq_quantities artifact validation and tenant/env enforcement if applicable.  
- Negative tests: missing semantic types logged but do not crash; unsupported type returns warning.

7. Docs & examples  
- Update this phase doc with formula table (type → quantity calculation), meta fields, and caching rules.  
- Update lane_B master plan quantities section.  
- Example: POST /cad/semantics → cad_semantics_id; POST /cad/boq_quantities → BoQ artifact with wall/slab counts and hash.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If BoQ schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD04 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
