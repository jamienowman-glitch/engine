# CAD TODO – Rhino-lite Work Packets

Scope: docs-only registry of feral-worker tasks for CAD ingest → semantics → BoQ → cost → plan → diff. Lane = CAD. Respect phase STOP RULEs; stay within listed folders/files.

## Stream: Ingest / Topology (CAD01)
- **id:** CAD01-INGEST-UNITS-DETECT (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD01_ingest_P0_P2.md  
  **stream:** Ingest  
  **root_folder:** engines/cad_ingest/  
  **file_scope:** service.py, models.py, dxf_adapter.py, ifc_lite_adapter.py, tests/test_ingest_dxf.py, tests/test_ingest_ifc_lite.py  
  **summary:** Enforce unit detection/normalization (mm/cm/m/ft/in) with clear errors when missing/ambiguous; include units in CadModel meta and responses.  
  **definition_of_done:** Ingest rejects unknown units unless hint provided; normalized units recorded on CadModel/meta; tests assert detection for DXF/IFC fixtures, error on missing units, and response units field; no other formats added.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/cad_ingest/ files listed.  
  **size:** M

- **id:** CAD01-HEAL-TOPOLOGY-TOLERANCE (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD01_ingest_P0_P2.md  
  **stream:** Topology  
  **root_folder:** engines/cad_ingest/  
  **file_scope:** topology_heal.py, tests/test_topology_heal.py  
  **summary:** Implement gap-close/vertex-dedup/winding normalization with tolerance and record healing_actions; validate divergence bounds.  
  **definition_of_done:** Healing functions apply tolerance parameter; healing_actions logged with counts/kinds; tests cover gap close, dedup, winding normalize, and divergence rejection; no other modules touched.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/cad_ingest/topology_heal.py and tests/test_topology_heal.py.  
  **size:** S

- **id:** CAD01-CACHE-KEY-IDEMPOTENT (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD01_ingest_P0_P2.md  
  **stream:** Ingest  
  **root_folder:** engines/cad_ingest/  
  **file_scope:** service.py, tests/test_service.py  
  **summary:** Ensure ingest cache key uses source_sha256 + params; reuse cached model deterministically and surface model_hash in response.  
  **definition_of_done:** Cache hit returns same model_hash/meta; cache miss stores model; tests assert cache reuse on identical params and miss on changed tolerance/grid; response includes model_hash.  
  **dependencies:** CAD01-INGEST-UNITS-DETECT  
  **agent_scope_hint:** Scope to engines/cad_ingest/service.py and tests/test_service.py.  
  **size:** S

- **id:** CAD01-ARTIFACT-REGISTRATION-PREFIX (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD01_ingest_P0_P2.md  
  **stream:** Ingest  
  **root_folder:** engines/media_v2/  
  **file_scope:** models.py, tests/test_media_v2_endpoints.py  
  **summary:** Register `cad_model` artifacts with required meta (format, units, tolerance_used, adapter_version, source_sha256) and enforce tenant/env + prefix.  
  **definition_of_done:** DerivedArtifact validation rejects missing tenant/env/meta; prefix guard in place; tests assert acceptance of valid payload and rejection of missing fields; no other kinds changed; doc note in geometry_cad_program master plan updated.  
  **dependencies:** CAD01-INGEST-UNITS-DETECT  
  **agent_scope_hint:** Scope to engines/media_v2/models.py and tests/test_media_v2_endpoints.py.  
  **size:** S

- **id:** CAD01-ROUTE-CONTEXT-VALIDATION (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD01_ingest_P0_P2.md  
  **stream:** Ingest  
  **root_folder:** engines/cad_ingest/  
  **file_scope:** routes.py, tests/test_ingest_dxf.py, tests/test_ingest_ifc_lite.py  
  **summary:** Enforce RequestContext tenant/env match on ingest route; reject missing context; keep HTTP contract.  
  **definition_of_done:** Route rejects tenant/env mismatch and missing context; happy-path still works; tests cover rejection and success; no schema changes.  
  **dependencies:** none  
  **agent_scope_hint:** Scope to engines/cad_ingest/routes.py and listed tests.  
  **size:** S

## Stream: Semantics / Graph (CAD02)
- **id:** CAD02-LAYER-RULES-CONFIG (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD02_semantics_P3_P5.md  
  **stream:** Semantics  
  **root_folder:** engines/cad_semantics/  
  **file_scope:** rules.py, service.py, models.py, tests/test_semantics_dxf.py, tests/test_semantics_ifc_lite.py  
  **summary:** Implement configurable layer/type heuristics (walls/doors/windows/slabs/columns/rooms) with overrides and rule_version meta.  
  **definition_of_done:** Default rules classify fixtures correctly; overrides change classification; meta records rule_version/overrides; tests assert defaults and override behavior; no new types introduced.  
  **dependencies:** CAD01-ARTIFACT-REGISTRATION-PREFIX  
  **agent_scope_hint:** Scope to engines/cad_semantics/ rules/service/models and listed tests.  
  **size:** M

- **id:** CAD02-LEVEL-DETECTION (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD02_semantics_P3_P5.md  
  **stream:** Semantics  
  **root_folder:** engines/cad_semantics/  
  **file_scope:** rules.py, graph.py, tests/test_semantics_dxf.py, tests/test_semantics_ifc_lite.py  
  **summary:** Infer levels/elevations from CadModel (z clustering/fallback defaults) and attach level_id to elements.  
  **definition_of_done:** Elements have level_id when data available; defaults applied with warning when missing; tests assert level inference on fixtures and deterministic IDs; meta includes level detection summary.  
  **dependencies:** CAD02-LAYER-RULES-CONFIG  
  **agent_scope_hint:** Scope to engines/cad_semantics/ rules.py, graph.py, listed tests.  
  **size:** S

- **id:** CAD02-SPATIAL-GRAPH-ADJ-CONN (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD02_semantics_P3_P5.md  
  **stream:** Graph  
  **root_folder:** engines/cad_semantics/  
  **file_scope:** graph.py, tests/test_spatial_graph.py  
  **summary:** Build adjacency/containment/connectivity graph with deterministic ordering and graph hash in meta.  
  **definition_of_done:** Graph nodes/edges sorted deterministically; graph hash computed; tests assert adjacency/containment/connectivity on synthetic fixture and determinism across runs.  
  **dependencies:** CAD02-LAYER-RULES-CONFIG  
  **agent_scope_hint:** Scope to engines/cad_semantics/graph.py and tests/test_spatial_graph.py.  
  **size:** S

- **id:** CAD02-SEMANTIC-ARTIFACT-META (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD02_semantics_P3_P5.md  
  **stream:** Semantics  
  **root_folder:** engines/media_v2/  
  **file_scope:** models.py, tests/test_media_v2_endpoints.py  
  **summary:** Register `cad_semantics` artifacts with meta (rule_version, source_cad_model_id, element_counts, graph_stats, cache_key) and tenant/env enforcement.  
  **definition_of_done:** Validator checks required meta and cache_key; tests assert rejection of missing fields and acceptance of valid payload; no other kinds changed.  
  **dependencies:** CAD02-LAYER-RULES-CONFIG  
  **agent_scope_hint:** Scope to engines/media_v2/models.py and tests/test_media_v2_endpoints.py.  
  **size:** S

## Stream: Quantities (CAD03)
- **id:** CAD03-WALL-AREA-OPENINGS (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD03_quantities_P6.md  
  **stream:** Quantities  
  **root_folder:** engines/boq_quantities/  
  **file_scope:** formulas.py, service.py, tests/test_quantities_dxf.py, tests/test_quantities_ifc_lite.py  
  **summary:** Compute wall length/area with opening deductions and tolerances; record formula_used and calc_version per item.  
  **definition_of_done:** BoQ items for walls include quantity/unit and formula_used; openings deducted; meta includes calc_version/tolerance; tests assert expected quantities on fixtures and deterministic ordering.  
  **dependencies:** CAD02-LAYER-RULES-CONFIG  
  **agent_scope_hint:** Scope to engines/boq_quantities/ formulas.py, service.py, listed tests.  
  **size:** M

- **id:** CAD03-SCOPE-TAGGING-LEVEL-ZONE (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD03_quantities_P6.md  
  **stream:** Quantities  
  **root_folder:** engines/boq_quantities/  
  **file_scope:** models.py, service.py, tests/test_quantities_determinism.py  
  **summary:** Tag BoQ items with level/zone scopes derived from semantics; ensure deterministic sort/hash.  
  **definition_of_done:** Items sorted by type then id; scope fields populated or None; hash/meta recorded; tests assert determinism and scope presence; no route changes.  
  **dependencies:** CAD02-LEVEL-DETECTION  
  **agent_scope_hint:** Scope to engines/boq_quantities/ models.py, service.py, tests/test_quantities_determinism.py.  
  **size:** S

- **id:** CAD03-ARTIFACT-META-HASH (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD03_quantities_P6.md  
  **stream:** Quantities  
  **root_folder:** engines/media_v2/  
  **file_scope:** models.py, tests/test_media_v2_endpoints.py  
  **summary:** Register `boq_quantities` artifacts with meta (calc_version, source_semantics_id, counts by type, hash) and tenant/env enforcement.  
  **definition_of_done:** Validator requires fields; tests assert rejection of missing fields and acceptance of correct payload; no other kinds changed.  
  **dependencies:** CAD03-WALL-AREA-OPENINGS  
  **agent_scope_hint:** Scope to engines/media_v2/models.py and tests/test_media_v2_endpoints.py.  
  **size:** S

## Stream: Costing (CAD04)
- **id:** CAD04-CATALOG-VERSIONING (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD04_costing_P7_P8.md  
  **stream:** Costing  
  **root_folder:** engines/boq_costing/  
  **file_scope:** catalog.py, service.py, models.py, tests/test_costing_defaults.py, tests/test_costing_overrides.py  
  **summary:** Implement rate catalog versioning with defaults and overrides; validate completeness vs BoQ types and reject unknown types unless allowed.  
  **definition_of_done:** Default catalog covers fixture BoQ; overrides per request work; missing rate yields warning or error per flag; tests assert catalog_version/meta, override behavior, and warnings; no new BoQ types.  
  **dependencies:** CAD03-ARTIFACT-META-HASH  
  **agent_scope_hint:** Scope to engines/boq_costing/ catalog.py, service.py, models.py, listed tests.  
  **size:** M

- **id:** CAD04-CURRENCY-FX-TABLE (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD04_costing_P7_P8.md  
  **stream:** Costing  
  **root_folder:** engines/boq_costing/  
  **file_scope:** service.py, tests/test_costing_overrides.py  
  **summary:** Add static FX table and currency conversion; record original and converted totals in meta.  
  **definition_of_done:** Service converts totals when currency differs; meta includes currency, fx_rate, totals_by_currency; tests assert conversion correctness and meta fields; defaults remain deterministic.  
  **dependencies:** CAD04-CATALOG-VERSIONING  
  **agent_scope_hint:** Scope to engines/boq_costing/service.py and tests/test_costing_overrides.py.  
  **size:** S

- **id:** CAD04-ARTIFACT-META-TOTALS (DONE)  
  **lane:** CAD  
  **phase:** PHASE_CAD04_costing_P7_P8.md  
  **stream:** Costing  
  **root_folder:** engines/media_v2/  
  **file_scope:** models.py, tests/test_media_v2_endpoints.py  
  **summary:** Register `boq_cost` artifacts with meta (catalog_version, currency, totals by category, hash, source_boq_id) and tenant/env enforcement.  
  **definition_of_done:** Validator requires fields; tests assert rejection of missing fields and acceptance of valid payload; no other kinds changed.  
  **dependencies:** CAD04-CATALOG-VERSIONING  
  **agent_scope_hint:** Scope to engines/media_v2/models.py and tests/test_media_v2_endpoints.py.  
  **size:** S

## Stream: Plan-of-Works (CAD05)
- **id:** CAD05-TASK-TEMPLATES-DURATIONS  
  **lane:** CAD  
  **phase:** PHASE_CAD05_plan_of_works_P9.md  
  **stream:** Plan  
  **root_folder:** engines/plan_of_work/  
  **file_scope:** templates.py, service.py, tests/test_plan_from_boq.py  
  **summary:** Map BoQ categories to task templates with duration formulas using productivity rates; store template_version in meta.  
  **definition_of_done:** Templates cover walls/slabs/openings/columns/rooms; durations computed from quantities; meta includes template_version; tests assert task counts/durations for fixtures and template_version presence.  
  **dependencies:** CAD04-ARTIFACT-META-TOTALS  
  **agent_scope_hint:** Scope to engines/plan_of_work/templates.py, service.py, tests/test_plan_from_boq.py.  
  **size:** M

- **id:** CAD05-DAG-CRITICAL-PATH  
  **lane:** CAD  
  **phase:** PHASE_CAD05_plan_of_works_P9.md  
  **stream:** Plan  
  **root_folder:** engines/plan_of_work/  
  **file_scope:** service.py, models.py, tests/test_plan_critical_path.py, tests/test_plan_determinism.py  
  **summary:** Build deterministic DAG, compute critical path duration/float, and hash; include dependencies per category order (foundation→structure→envelope→finishes).  
  **definition_of_done:** Tasks sorted deterministically; critical_path_days/meta recorded; tests assert DAG acyclic, critical path value, determinism across runs; no route changes.  
  **dependencies:** CAD05-TASK-TEMPLATES-DURATIONS  
  **agent_scope_hint:** Scope to engines/plan_of_work/service.py, models.py, listed tests.  
  **size:** M

- **id:** CAD05-PLAN-ARTIFACT-META  
  **lane:** CAD  
  **phase:** PHASE_CAD05_plan_of_works_P9.md  
  **stream:** Plan  
  **root_folder:** engines/media_v2/  
  **file_scope:** models.py, tests/test_media_v2_endpoints.py  
  **summary:** Register `plan_of_work` artifacts with meta (task_count, critical_path_days, template_version, hash, source_cost_id) and tenant/env enforcement.  
  **definition_of_done:** Validator requires fields; tests assert rejection of missing fields and acceptance of valid payload; no other kinds changed.  
  **dependencies:** CAD05-DAG-CRITICAL-PATH  
  **agent_scope_hint:** Scope to engines/media_v2/models.py and tests/test_media_v2_endpoints.py.  
  **size:** S

## Stream: Diff / Change Tracking (CAD06)
- **id:** CAD06-SEMANTIC-DIFF  
  **lane:** CAD  
  **phase:** PHASE_CAD06_diffs_and_change_tracking_P10.md  
  **stream:** Diff  
  **root_folder:** engines/cad_diff/  
  **file_scope:** service.py, models.py, tests/test_cad_diff.py  
  **summary:** Compute adds/removes/changes between two cad_semantics artifacts with stable IDs; classify move/resize/type-change; produce diff hash.  
  **definition_of_done:** Diff lists added/removed/modified elements with change_type; hash deterministic; tests assert detection on fixture edits and determinism; RequestContext respected.  
  **dependencies:** CAD02-SEMANTIC-ARTIFACT-META  
  **agent_scope_hint:** Scope to engines/cad_diff/service.py, models.py, tests/test_cad_diff.py.  
  **size:** M

- **id:** CAD06-IMPACT-BOQ-COST-PLAN  
  **lane:** CAD  
  **phase:** PHASE_CAD06_diffs_and_change_tracking_P10.md  
  **stream:** Diff  
  **root_folder:** engines/cad_diff/  
  **file_scope:** service.py, tests/test_cad_diff.py  
  **summary:** Map semantic diffs to BoQ and cost deltas and flag impacted plan tasks with severity tags; include meta with source artifact IDs.  
  **definition_of_done:** For given old/new artifacts, diff includes BoQ delta summary and impacted plan tasks with severity; tests assert delta computation on fixture change and meta fields; deterministic ordering.  
  **dependencies:** CAD06-SEMANTIC-DIFF, CAD04-ARTIFACT-META-TOTALS, CAD05-PLAN-ARTIFACT-META  
  **agent_scope_hint:** Scope to engines/cad_diff/service.py and tests/test_cad_diff.py.  
  **size:** M
