1. Goal  
Support multi-project portfolio rollups and lifecycle states for CAD/cost/plan artifacts.

2. Scope (In / Out)  
- In: portfolio models, lifecycle status transitions (draft/review/approved/etc.), aggregations over cost/risk/schedule.  
- Out: external integrations (next phase), UI/auth/tenant/safety.

3. Modules to touch  
- engines/cad_portfolio/*  
- engines/cad_portfolio/tests/*  
- engines/boq_costing/models.py (read-only unless summary fields needed)  
- engines/plan_of_work/models.py (read-only unless summary fields needed)  
- engines/cad_risk_scoring/models.py (read-only unless summary fields needed)  
- docs/engines/geometry_cad_program/PHASE_CAD08_portfolio_and_lifecycle_P13_P14.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Define Portfolio model: list of project references with aggregates (total cost, risk score, schedule duration, counts), deterministic ordering.  
- Implement lifecycle states for artifacts (draft/review/approved) with allowed transitions and validation; store state + timestamps + actor (if available).  
- Add aggregation functions to consume outputs from costing/plan/risk modules; handle missing artifacts gracefully with warnings.  
- Provide portfolio summary artifact (JSON) with version/meta; optional per-project deltas vs previous snapshot.  
- Validate inputs: ensure projects exist; prevent invalid state transitions; deterministic IDs/hashes for portfolio snapshots.  
- Keep existing artifacts untouched; tag CONTRACT CHANGE if adding lifecycle fields to shared schemas.

5. Tests  
- engines/cad_portfolio/tests: aggregation with 2–3 sample projects, lifecycle transition validation, handling missing artifacts gracefully, deterministic ordering.  
- Edge cases: invalid transitions raise errors; empty portfolio yields empty aggregates.

6. Docs  
- Update this phase doc with portfolio schema, lifecycle state machine, aggregation examples, and warning behaviors.  
- Note any lifecycle fields added to artifacts in ENGINE_INVENTORY/REGISTRY if applicable.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- Keep interfaces stable; tag CONTRACT CHANGE if lifecycle fields added and update only in-lane consumers.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD09 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD08_portfolio_and_lifecycle_P13_P14

1. Goal  
Aggregate multiple projects’ artifacts into a portfolio view with lifecycle states, summaries, and comparisons.

2. North star + Definition of Done  
- North star slice: portfolio-lite dashboard—aggregate cad_model/semantics/BoQ/cost/plan/risk artifacts across projects, compute rollups, and track lifecycle states (draft/review/approved/archived) deterministically.  
- Definition of Done:  
  - Workers can POST portfolio aggregation requests and receive a `cad_portfolio` artifact (media_v2) summarizing totals (quantities, costs, risks) across projects, with lifecycle state per project and comparisons vs baselines.  
  - Supports pagination and filters by lifecycle state; meta includes aggregation_version, project_count, hash.  
  - Tests prove correct rollups on multi-project fixtures, deterministic ordering/hash, and lifecycle transitions.

3. Scope (In / Out)  
- In: portfolio models, aggregation service/routes, lifecycle state transitions, artifact registration.  
- Out: API surfacing beyond allow-listed routes, UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/cad_portfolio/models.py  
- engines/cad_portfolio/service.py  
- engines/cad_portfolio/routes.py  
- engines/cad_portfolio/aggregations.py  
- engines/cad_portfolio/tests/test_portfolio_rollup.py  
- engines/cad_portfolio/tests/test_portfolio_lifecycle.py  
- engines/cad_portfolio/tests/test_portfolio_determinism.py  
- engines/cad_risk_scoring/models.py (READ-ONLY unless schema change marked CONTRACT CHANGE)  
- engines/plan_of_work/models.py (READ-ONLY unless schema change marked)  
- engines/boq_costing/models.py (READ-ONLY unless schema change marked)  
- engines/media_v2/models.py (only to register cad_portfolio artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for cad_portfolio artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD08_portfolio_and_lifecycle_P13_P14.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (portfolio summary only)  
- READ-ONLY context: ingestion/semantics/BoQ/cost/plan/diff/risk modules unless noted.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define `PortfolioProject` and `PortfolioSummary` schemas (project_id, lifecycle_state, totals for quantities/cost/risk counts, baselines) and `cad_portfolio` artifact meta (aggregation_version, project_count, hash, filters).  
  - Register artifact kind in media_v2.  
- Aggregations  
  - Implement rollups for cost totals, risk severity counts, plan durations, and key BoQ categories across projects.  
  - Support filters by lifecycle state and date; enforce deterministic ordering of projects.  
- Lifecycle handling  
  - Add lifecycle state transitions (draft/review/approved/archived) with validation rules; record transitions in meta.  
- Service & routes  
  - In service.py: accept list of artifact ids per project (cost/plan/risk), aggregate summaries, apply filters, compute hash, register cad_portfolio artifact; support caching by inputs + filters + aggregation_version.  
  - In routes.py: POST /cad/portfolio endpoint with project artifact references and filters; RequestContext required but unchanged.  
- Validation & errors  
  - Validate referenced artifacts exist and belong to allowed stages; clear errors for missing data; allow partial aggregation with warnings.  
- Fixtures  
  - Create multi-project fixture set (at least two projects) with known totals; expected rollups/hashes documented in tests.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/cad_portfolio/tests/test_portfolio_rollup.py: rollups for multi-project fixtures; totals and ordering/hash assertions.  
- engines/cad_portfolio/tests/test_portfolio_lifecycle.py: lifecycle transitions, validation, and meta updates.  
- engines/cad_portfolio/tests/test_portfolio_determinism.py: same inputs → same portfolio/hash; cache hit/miss on filter changes.  
- engines/media_v2/tests/test_media_v2_endpoints.py: cad_portfolio artifact validation and tenant/env enforcement if applicable.  
- Negative tests: partial data produces warnings but not crashes; invalid lifecycle transition rejected.

7. Docs & examples  
- Update this phase doc with lifecycle state machine, rollup fields, meta fields.  
- Update lane_B master plan portfolio section.  
- Example: Provide two projects with cost/plan/risk artifacts; POST /cad/portfolio with filter=approved → aggregated totals and lifecycle states in artifact meta.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD09 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
