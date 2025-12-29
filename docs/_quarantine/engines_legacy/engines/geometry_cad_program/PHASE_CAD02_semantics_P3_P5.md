1. Goal  
Classify CAD elements, map layers to semantic types, and build a spatial graph.

2. Scope (In / Out)  
- In: semantic classification rules, layer mapping, spatial graph construction, ingest metadata augmentation if needed.  
- Out: quantities/BoQ/cost (later phases), UI/auth/tenant/safety.

3. Modules to touch  
- engines/cad_semantics/*  
- engines/cad_semantics/tests/*  
- engines/cad_ingest/models.py (only if exposing metadata needed)  
- engines/cad_ingest/tests/* (only if models change)  
- engines/media_v2/models.py (only if semantic artifacts registered)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if semantic artifacts registered)  
- docs/engines/geometry_cad_program/PHASE_CAD02_semantics_P3_P5.md  
- docs/engines/ENGINE_INVENTORY.md (only if artifact kinds added)  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Define SemanticElement schema (type, geometry ref, attributes, level/elevation) with stable IDs; version schema.  
- Implement layer/type mapping rules (walls/doors/windows/slabs/columns) via heuristics + config; allow overrides per project.  
- Build spatial graph: adjacency (touching edges), containment (rooms within levels), connectivity (door connects rooms), and level detection; record relationships.  
- Normalize elevations/levels and record story heights; handle missing level data gracefully with defaults.  
- Validate against sample CAD fixtures; produce deterministic IDs and consistent ordering of elements/graph edges.  
- Persist semantic results (JSON) possibly as media_v2 artifacts with meta (rule version, confidence).  
- Keep CadModel compatibility; tag CONTRACT CHANGE if adding fields.

5. Tests  
- engines/cad_semantics/tests: classification correctness on sample drawing (walls/doors/windows/slabs), level detection, adjacency/containment assertions.  
- Determinism tests: same input → same element IDs/types/graph edges.  
- Error path tests: unknown layers/empty model handled gracefully.

6. Docs  
- Update this phase doc with semantic rules reference, config knobs, and sample graph diagrams.  
- Note schema/version in geometry_cad_program docs.  
- Update ENGINE_INVENTORY if new artifact kind registered.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If CadModel/semantic schema changes or new artifacts are added, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD03 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD02_semantics_P3_P5

1. Goal  
Classify ingested CAD elements into semantic building types and build a spatial graph that downstream BoQ/cost/plan can consume.

2. North star + Definition of Done  
- North star slice: Rhino/IFC-lite semantics that tag layers/elements as walls/doors/windows/slabs/columns/rooms/levels and emit a spatial graph (adjacency, containment, connectivity) with stable IDs for a small real plan.  
- Definition of Done:  
  - Workers can take a `cad_model` artifact and produce a `cad_semantics` artifact (media_v2) with typed `SemanticElement`s and a spatial graph (adjacency/containment/connectivity) keyed by deterministic IDs.  
  - Layer/type rules configurable; default heuristics handle common naming conventions; elevation/level detection included.  
  - Deterministic ordering/IDs across runs; rule version recorded in meta.  
  - Tests on at least one DXF and one IFC-lite fixture prove correct counts/types, graph edges, and determinism; error paths for unknown layers handled gracefully.

3. Scope (In / Out)  
- In: semantic classification rules, layer mapping, level detection, spatial graph construction, semantic artifacts + meta.  
- Out: BoQ/cost/plan/diff/risk/portfolio, UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/cad_semantics/models.py  
- engines/cad_semantics/service.py  
- engines/cad_semantics/routes.py  
- engines/cad_semantics/rules.py (classification heuristics)  
- engines/cad_semantics/graph.py  
- engines/cad_semantics/tests/test_semantics_dxf.py  
- engines/cad_semantics/tests/test_semantics_ifc_lite.py  
- engines/cad_semantics/tests/test_spatial_graph.py  
- engines/cad_ingest/models.py (only if SemanticElement needs ingest metadata exposure)  
- engines/cad_ingest/tests/* (only if CadModel fields change)  
- engines/media_v2/models.py (only to register cad_semantics artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for cad_semantics artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD02_semantics_P3_P5.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (semantics summary only)  
- READ-ONLY context: boq/cost/plan/diff/risk/portfolio modules and docs not listed above.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define/confirm `SemanticElement` (id, type, geometry_ref, attributes, level/elevation, rule_version, confidence) and `SpatialGraph` structures (nodes, adjacency edges, containment edges, connectivity).  
  - Register `cad_semantics` artifact schema in media_v2 with meta (rule_version, adapter_version, source_cad_model_id, element_counts, graph_stats).  
- Classification rules  
  - Implement layer/name heuristics for walls/doors/windows/slabs/columns/rooms/levels; allow overrides via config in service.  
  - Add geometry-based hints (aspect ratio/length/closed polyline) to disambiguate.  
  - Record per-element rule hits/confidence for traceability.  
- Level and elevation handling  
  - Normalize elevations from CadModel; infer missing levels via z clustering; attach level_id to elements.  
- Spatial graph  
  - Build adjacency (touching walls), containment (rooms within levels), connectivity (door connects rooms), circulation edges.  
  - Ensure deterministic ordering of nodes/edges; include graph hash in meta.  
- Service & routes  
  - In service.py: load cad_model artifact, apply rules, build graph, register cad_semantics artifact; support caching by cad_model_id + rule_version + overrides.  
  - In routes.py: POST /cad/semantics to accept cad_model_id and rule overrides; return artifact id/meta; validate RequestContext presence only (no auth changes).  
- Validation & compatibility  
  - Validate required fields present in CadModel before processing; error clearly if missing.  
  - Keep backward compatibility if CadModel gains new fields; mark CONTRACT CHANGE as needed.  
- Fixtures  
  - Use ingest fixtures from CAD01; expected semantic counts per fixture documented in tests.  
  - Add small malformed-layer fixture to test graceful handling.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/cad_semantics/tests/test_semantics_dxf.py: classification counts/types, level detection, rule_version meta, determinism across runs.  
- engines/cad_semantics/tests/test_semantics_ifc_lite.py: same for IFC-lite.  
- engines/cad_semantics/tests/test_spatial_graph.py: adjacency/containment/connectivity correctness on synthetic fixtures; graph hash determinism.  
- engines/media_v2/tests/test_media_v2_endpoints.py: cad_semantics artifact validation, tenant/env enforcement if applicable.  
- Negative tests: unknown layers fall back to `unknown` type with warning; cache hit/miss when rule overrides differ.

7. Docs & examples  
- Update this phase doc with rule tables (layer name patterns → type), graph schema, meta fields, caching knobs.  
- Update lane_B master plan semantics section.  
- Example: POST /cad/ingest → cad_model_id; POST /cad/semantics with defaults → cad_semantics artifact id/meta showing counts and graph stats.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If CadModel or SemanticElement schemas/artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD03 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
