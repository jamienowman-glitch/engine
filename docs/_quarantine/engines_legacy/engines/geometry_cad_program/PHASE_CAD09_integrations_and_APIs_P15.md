1. Goal  
Expose consolidated CAD/BoQ/Cost/Plan/Risk APIs and artifacts with deterministic contracts.

2. Scope (In / Out)  
- In: FastAPI routes for ingest→plan pipeline, artifact registration, schema docs, deterministic outputs.  
- Out: UI/auth/spine/orchestration; external integrations beyond API exposure.

3. Modules to touch  
- engines/cad_ingest/routes.py  
- engines/cad_semantics/routes.py  
- engines/boq_quantities/routes.py  
- engines/boq_costing/routes.py  
- engines/plan_of_work/routes.py  
- engines/cad_diff/routes.py  
- engines/cad_risk_scoring/routes.py  
- engines/cad_ingest/tests (route tests)  
- engines/cad_semantics/tests (route tests)  
- engines/boq_quantities/tests (route tests)  
- engines/boq_costing/tests (route tests)  
- engines/plan_of_work/tests (route tests)  
- engines/cad_diff/tests (route tests)  
- engines/cad_risk_scoring/tests (route tests)  
- engines/media_v2/models.py (only if registering artifacts for pipeline endpoints)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if artifact registration changes)  
- docs/engines/geometry_cad_program/PHASE_CAD09_integrations_and_APIs_P15.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.
- Do not touch unrelated engines/UI/core.

4. Implementation checklist  
- Define clear request/response models per stage and for a full pipeline endpoint (ingest→semantics→quantities→cost→plan→risk/diff).  
- Register artifacts via media_v2 for CAD model, BoQ, cost summary, plan, diff, risk report; link upstream/downstream IDs in meta.  
- Ensure deterministic IDs/orderings; add pagination for list endpoints; consistent error responses.  
- Provide health/version endpoints for each service; include schema version in responses.  
- Surface CONTRACT CHANGE if any models adjusted; update all in-lane callers.  
- Add minimal dependency checks/logging; no auth added.  
- Validate inputs (file types, project IDs) and return structured errors; avoid side effects on failure.

5. Tests  
- Route tests per module: sample CAD through pipeline, verifying artifacts created/linked and outputs deterministic.  
- Error-path tests: invalid inputs return clear errors, pagination works, missing artifacts handled gracefully.  
- Regression test: same input produces identical outputs/ids.  
- Mock external deps; avoid heavy file sizes in CI.

6. Docs  
- Update this phase doc with API reference per route, expected artifacts, and linkage diagram.  
- Add end-to-end walkthrough from upload → plan → risk.  
- Note schema versions and CONTRACT CHANGE locations.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed.  
- Keep HTTP signatures stable unless explicitly tagged CONTRACT CHANGE and updated in-lane.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. This finishes Lane B; stop only if TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD09_integrations_and_APIs_P15

1. Goal  
Expose stable HTTP APIs for the entire CAD pipeline (ingest → semantics → BoQ → cost → plan → diff → risk → portfolio) with artifact registration and pagination, suitable for single-tenant “Rhino-lite” usage.

2. North star + Definition of Done  
- North star slice: pipeline API—callable endpoints that let a user submit CAD files and retrieve linked artifacts for every stage, plus a single pipeline endpoint that orchestrates the sequence and returns a manifest of artifact ids.  
- Definition of Done:  
  - Routes exist for each stage (ingest, semantics, quantities, cost, plan, diff, risk, portfolio) with request/response schemas documented and deterministic outputs.  
  - A pipeline endpoint accepts inputs (file/URI + options) and runs the chain, returning artifact ids and meta links; supports idempotency via source hash.  
  - media_v2 artifacts linked (source_id fields) to enable tracing; pagination supported for list endpoints; deterministic ordering.  
  - Tests cover route contracts, pipeline happy path, failure propagation, and determinism with fixtures.

3. Scope (In / Out)  
- In: API routes for CAD stages, pipeline orchestration in service, artifact linkage fields, docs.  
- Out: auth/tenant enforcement changes, UI, orchestration outside engines, connectors/vector stores/logging changes, cost/plan/risk logic (handled in prior phases).

4. Modules to touch (hard allow-list)  
- engines/cad_ingest/routes.py (API contracts only)  
- engines/cad_semantics/routes.py (API contracts only)  
- engines/boq_quantities/routes.py (API contracts only)  
- engines/boq_costing/routes.py (API contracts only)  
- engines/plan_of_work/routes.py (API contracts only)  
- engines/cad_diff/routes.py (API contracts only)  
- engines/cad_risk_scoring/routes.py (API contracts only)  
- engines/cad_portfolio/routes.py (API contracts only)  
- engines/cad_pipeline/service.py (new or existing orchestrator)  
- engines/cad_pipeline/routes.py  
- engines/cad_pipeline/tests/test_pipeline_end_to_end.py  
- engines/cad_pipeline/tests/test_pipeline_idempotency.py  
- engines/media_v2/models.py (only to add linkage fields if needed; mark CONTRACT CHANGE)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if linkage fields added)  
- docs/engines/geometry_cad_program/PHASE_CAD09_integrations_and_APIs_P15.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (API summary only)  
- docs/engines/ENGINE_MUSCLE_RECON_v1.md (only if referencing updated artifacts; optional)  
- READ-ONLY context: underlying stage services; do not change their business logic in this phase.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- API contracts  
  - Document request/response schemas for each stage; ensure consistent field names (artifact_id, meta, source_id).  
  - Add pagination to list endpoints if not present; deterministic ordering and filters by source_id.  
- Pipeline orchestrator  
  - Implement cad_pipeline service to run ingest → semantics → BoQ → cost → plan (optionally risk); accept options for catalogs/rule_versions; propagate meta and source links.  
  - Add idempotency: detect existing artifacts via source hash + params; reuse instead of re-running when matching.  
  - Propagate failures with clear stage attribution; partial successes recorded in meta.  
- Routes  
  - Add cad_pipeline route (POST /cad/pipeline) returning manifest of artifact ids/meta; ensure RequestContext required but unchanged.  
  - Update individual stage routes for consistent path naming and response shapes; mark CONTRACT CHANGE if needed.  
- Artifact linkage  
  - Ensure artifacts include source references (e.g., cad_semantics.source_cad_model_id); add fields in media_v2 models if missing (CONTRACT CHANGE).  
  - Validate linkage in responses; include chain summary in pipeline response.  
- Determinism & logging  
  - Enforce deterministic ordering in pipeline outputs; include hash/versions in manifest.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/cad_pipeline/tests/test_pipeline_end_to_end.py: run full pipeline on DXF/IFC-lite fixtures; assert all artifact ids returned, linkage correct, deterministic hashes.  
- engines/cad_pipeline/tests/test_pipeline_idempotency.py: repeat pipeline call with same params → reused artifacts; changed params → new artifacts.  
- Stage route contract tests: minimal request/response schema validation for each updated route (can be in respective module tests or pipeline tests).  
- engines/media_v2/tests/test_media_v2_endpoints.py: linkage fields validation if added.  
- Negative tests: pipeline fails gracefully on missing stage output (e.g., ingest error).

7. Docs & examples  
- Update this phase doc with API tables for each route and pipeline, linkage fields, idempotency rules.  
- Update lane_B master plan API section.  
- Example: POST /cad/pipeline with floorplan.dxf + default options → manifest of cad_model, cad_semantics, boq_quantities, boq_cost, plan_of_work (and optional risk) artifact ids/meta.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If API contracts or artifact schemas change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then this lane is complete unless a genuine TODO – HUMAN DECISION REQUIRED blocks progress.
