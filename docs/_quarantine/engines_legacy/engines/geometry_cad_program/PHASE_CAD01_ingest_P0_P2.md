# PHASE_CAD01_ingest_P0_P2

1. Goal  
Normalize DXF/IFC-lite inputs into a deterministic `CadModel` with healed topology, consistent units, and stable IDs, producing artifacts that downstream semantics/BoQ/cost/plan phases can rely on.

2. North star + Definition of Done  
- North star slice: Rhino/IFC-lite ingest that can take small but real architectural drawings (e.g., floorplans, elevations) and emit a stable, unit-correct `CadModel` with validated topology and fixtures.  
- Definition of Done:  
  - Workers can POST a DXF/IFC-lite file (or URL) to ingest and receive a `CadModel` JSON artifact (media_v2) with normalized units, bounding boxes, layers, entities (lines/arcs/polylines/solids), topology graph, and stable deterministic IDs.  
  - Units conversion and origin normalization applied; missing/ambiguous units detected and rejected with clear errors.  
  - Topology healing rules applied (gap closing within tolerance, duplicate vertex collapse, winding normalization) with recorded `healing_actions` in meta.  
  - Large files stream-parsed with size/time guards; dev/prod paths separated; deterministic outputs across runs.  
  - Tests prove ingest on at least two fixtures (DXF floorplan, IFC-lite sample) yields expected element counts, bounding boxes, and hash-stable IDs.

3. Scope (In / Out)  
- In: cad_ingest parsing (DXF/IFC-lite), units normalization, topology healing, deterministic ID assignment, media_v2 artifact registration for `cad_model`, ingest routes/service contracts.  
- Out: semantics/classification, BoQ/cost, plan-of-works, UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/cad_ingest/models.py  
- engines/cad_ingest/service.py  
- engines/cad_ingest/routes.py  
- engines/cad_ingest/dxf_adapter.py  
- engines/cad_ingest/ifc_lite_adapter.py (or similarly named IFC-lite adapter)  
- engines/cad_ingest/topology_heal.py (healing helpers)  
- engines/cad_ingest/tests/test_ingest_dxf.py  
- engines/cad_ingest/tests/test_ingest_ifc_lite.py  
- engines/cad_ingest/tests/test_topology_heal.py  
- engines/media_v2/models.py (only to register cad_model artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for cad_model artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD01_ingest_P0_P2.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (ingest summary only)  
- READ-ONLY context: other cad_* modules, boq/plan/cost/risk/portfolio docs.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define/confirm `CadIngestRequest` (file upload or URI, format hint, unit hint, tolerance settings) and `CadModel` schema (units, origin, bbox, layers, entities with geometry payloads, topology graph, healing_actions, source_meta).  
  - Tag CONTRACT CHANGE if schemas change; update media_v2 artifact `cad_model` with meta fields (format, units, tolerance_used, healing_actions summary, source_sha256, adapter_version).  
- Adapters  
  - In dxf_adapter.py: stream-parse entities; map DXF types to internal primitives; apply unit conversion; detect/memoize layer names; attach source element ids.  
  - In ifc_lite_adapter.py: parse minimal IFC-lite subset (walls, slabs, windows/doors if present); flatten into primitives; preserve placement transforms; handle missing units via defaults/error.  
  - Add deterministic ID generation (hash of geometry + layer + source id) to ensure stable output.  
- Topology healing  
  - Implement gap-closing within tolerance, duplicate vertex collapse, winding normalization for closed polylines, and optional snap-to-grid; record actions in `healing_actions`.  
  - Add validation that healed geometry maintains area/length within tolerance bounds; reject if divergence too high.  
- Service & routes  
  - In service.py: orchestrate adapter selection, units normalization, topology heal, artifact registration; enforce size/time guards; support dev/prod storage differences without local temp in prod.  
  - In routes.py: POST /cad/ingest endpoint accepting upload/URI, returning cad_model artifact id + meta; enforce RequestContext presence but do not alter auth logic.  
  - Add caching by source_sha256 + params to reuse artifacts when identical request.  
- Determinism & validation  
  - Ensure ordering of layers/entities is deterministic (sorted by stable id); include hash of model in meta.  
  - Validate required fields (units, bbox, entity counts) and reject incomplete inputs with clear errors.  
- Fixtures  
  - Add at least two fixtures (DXF floorplan, IFC-lite sample); include expected counts/bboxes hashes in tests; document fixture hashes in tests to prevent drift.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/cad_ingest/tests/test_ingest_dxf.py: happy-path ingest of floorplan DXF, unit conversion correctness, deterministic IDs/hash, bbox/counts assertions, cache hit/miss with param changes.  
- engines/cad_ingest/tests/test_ingest_ifc_lite.py: same as above for IFC-lite sample; missing-unit error path.  
- engines/cad_ingest/tests/test_topology_heal.py: healing actions (gap close, dedup vertices, winding), tolerance guardrails, divergence rejection.  
- engines/media_v2/tests/test_media_v2_endpoints.py: cad_model artifact schema/meta validation, rejection of missing tenant/env, prefix enforcement.  
- Add failure-path tests for oversize file/timeouts (skipped if env lacks fixtures) and unknown format rejection.  
- Ensure determinism tests: same input → same IDs/hash/meta.

7. Docs & examples  
- Update this phase doc with schema tables for CadModel and cad_model artifact meta, adapter options, tolerance defaults.  
- Update lane_B master plan ingest section with the new Definition of Done.  
- Example walkthrough: POST /cad/ingest with floorplan.dxf → receive cad_model artifact id/hash/meta; describe tolerance/healing actions logged.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If CadModel schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD02 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
