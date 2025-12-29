1. Goal  
Apply costs to BoQ using a cost library with currency/version support.

2. Scope (In / Out)  
- In: cost catalog, rate application, static currency conversion, versioning, summaries.  
- Out: plan scheduling (next phase), UI/auth/tenant/safety.

3. Modules to touch  
- engines/boq_costing/*  
- engines/boq_costing/tests/*  
- engines/boq_quantities/models.py (read-only unless fields needed)  
- engines/boq_quantities/tests/* (only if schema changes)  
- docs/engines/geometry_cad_program/PHASE_CAD04_costing_P7_P8.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Define CostItem schema (boq_id, unit_rate, currency, total, source/catalog version, warnings) and ensure deterministic ordering.  
- Design cost catalog model with versioning and defaults; TODO – HUMAN DECISION REQUIRED: choose default currency (propose USD) and static FX table.  
- Apply costs to BoQ items with unit conversions, quantity x rate math, and fallbacks for missing rates (flag warnings and zero cost if allowed).  
- Support currency conversion using static FX table; include original currency and converted totals in meta.  
- Provide summaries by level/zone/discipline and overall totals; include contingency placeholders.  
- Validate inputs (unknown BoQ types, negative rates) with clear errors; ensure deterministic outputs given same catalog.  
- Keep BoQ schema compatibility; tag CONTRACT CHANGE if schema must change.

5. Tests  
- engines/boq_costing/tests: apply costs on sample BoQ, missing rate warning path, currency conversion correctness, deterministic totals with same catalog.  
- Edge cases: zero/negative quantities, unknown BoQ types handled gracefully.  
- Verify summaries per level/discipline are correct.

6. Docs  
- Update this phase doc with cost catalog format, currency policy, example calculations, and warning behaviors.  
- Add sample catalog/BoQ JSON and resulting cost output.  
- Note dependency on catalog versioning in geometry_cad_program docs.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If BoQ schema changes, mark CONTRACT CHANGE in this doc and update only explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD05 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD04_costing_P7_P8

1. Goal  
Convert BoQ quantities into cost estimates using rate catalogs, currencies, and versioned assumptions, producing cost artifacts ready for plan-of-works.

2. North star + Definition of Done  
- North star slice: QS-lite costing—given BoQ, apply rate catalogs and markups to produce reproducible `CostItem`s and rolled-up totals.  
- Definition of Done:  
  - Workers can POST a `boq_quantities` artifact and receive a `boq_cost` artifact (media_v2) with line-item `CostItem`s (scope, unit_rate, quantity, extended cost, currency, assumptions) and rollups by category.  
  - Supports rate catalogs with versioning and currency; defaults provided; overrides allowed per request.  
  - Deterministic totals and hash across runs; meta records catalog_version, currency, markup/tax, source_boq_id.  
  - Tests verify expected totals on fixtures, currency application, catalog overrides, and determinism; error paths for missing rates handled cleanly.

3. Scope (In / Out)  
- In: cost catalog models, cost calculation service/routes, cost artifact registration, currency/markup handling.  
- Out: plan-of-works generation, diffs/risk/portfolio, UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/boq_costing/models.py  
- engines/boq_costing/service.py  
- engines/boq_costing/routes.py  
- engines/boq_costing/catalog.py (rate catalog storage/helpers)  
- engines/boq_costing/tests/test_costing_defaults.py  
- engines/boq_costing/tests/test_costing_overrides.py  
- engines/boq_costing/tests/test_costing_determinism.py  
- engines/boq_quantities/models.py (only if exposing extra fields)  
- engines/boq_quantities/tests/* (only if schema changes)  
- engines/media_v2/models.py (only to register boq_cost artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for boq_cost artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD04_costing_P7_P8.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (costing summary only)  
- READ-ONLY context: plan/diff/risk/portfolio modules and docs not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define/confirm `CostItem` schema (id, boq_item_ref, unit_rate, quantity, currency, markup/tax, extended_cost, category, assumptions, calc_version).  
  - Register `boq_cost` artifact kind with meta (catalog_version, currency, totals by category, hash, source_boq_id).  
- Catalog  
  - Implement rate catalog loader with defaults (per type/unit), versioning, and optional project overrides; validate completeness vs BoQ types.  
  - Currency handling: allow specifying currency and conversion factor; enforce rounding rules.  
- Service & routes  
  - In service.py: load BoQ artifact, apply catalog, compute CostItems + rollups; register artifact; support caching by boq_id + catalog_version + currency + markup params.  
  - In routes.py: POST /cad/boq_cost endpoint with catalog/markup params; return artifact id/meta; validate RequestContext presence only.  
- Determinism & validation  
  - Sort CostItems deterministically; compute artifact hash; ensure repeated runs match.  
  - Clear errors for missing rates; allow fallback default with explicit flag.  
- Fixtures  
  - Use BoQ fixtures; expected totals and hashes documented in tests; include override catalog fixture.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/boq_costing/tests/test_costing_defaults.py: apply default catalog to BoQ fixture; assert totals, currency, hash determinism.  
- engines/boq_costing/tests/test_costing_overrides.py: catalog override + markup/tax; ensure correct totals and meta; cache hit/miss on param changes.  
- engines/boq_costing/tests/test_costing_determinism.py: same input → same CostItems/hash; missing rate error path.  
- engines/media_v2/tests/test_media_v2_endpoints.py: boq_cost artifact validation and tenant/env enforcement if applicable.

7. Docs & examples  
- Update this phase doc with catalog schema, default rates, currency/markup rules, meta fields.  
- Update lane_B master plan costing section.  
- Example: POST /cad/boq_quantities → boq_id; POST /cad/boq_cost with catalog_version=default → cost artifact totals/rollups/hash.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If CostItem schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD05 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
