1. Goal  
Score risks/compliance based on semantics/plan by applying deterministic rule sets.

2. Scope (In / Out)  
- In: risk rules, compliance checks, scoring outputs leveraging semantics and plan/task data.  
- Out: portfolio rollups (next phase), UI/auth/tenant/safety.

3. Modules to touch  
- engines/cad_risk_scoring/*  
- engines/cad_risk_scoring/tests/*  
- engines/plan_of_work/models.py (read-only unless fields needed)  
- engines/cad_semantics/models.py (read-only unless fields needed)  
- docs/engines/geometry_cad_program/PHASE_CAD07_risk_and_compliance_P11_P12.md  
- Treat all other files as read-only context.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Define RiskFinding schema (id, rule_id, type, severity, location, level/zone, source_ref, message) with deterministic ordering.  
- Implement rule set: spans without support, wall height/thickness limits, missing egress, schedule over-allocation, code clearances; make rules configurable per code set.  
- Compliance flags per rule set with pass/warn/fail states; aggregate risk score with weighted severity.  
- Evaluate rules deterministically; include meta (rule_version, inputs used) and warnings for missing data rather than crashing.  
- Map findings back to impacted BoQ/plan tasks where applicable for traceability.  
- Optional: register risk report artifact via media_v2 with summary + per-finding list.  
- Keep plan/semantics schemas stable; tag CONTRACT CHANGE if fields added.

5. Tests  
- engines/cad_risk_scoring/tests: sample models triggering known rules with expected severities; deterministic ordering.  
- Edge cases: missing data produces warnings not crashes; rule set config switches codes.  
- Integration test: findings reference plan tasks and semantic IDs correctly.

6. Docs  
- Update this phase doc with rule catalogue, scoring method, configuration knobs, and examples.  
- Add sample risk report JSON.  
- Note dependencies on plan/semantics versions.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- Keep interfaces stable; tag CONTRACT CHANGE if adding fields to plan/semantics and update only in-lane consumers.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Then proceed to PHASE_CAD08 unless blocked by TODO – HUMAN DECISION REQUIRED.
# PHASE_CAD07_risk_and_compliance_P11_P12

1. Goal  
Score risks and compliance findings from CAD semantics/BoQ/cost/plan artifacts using deterministic rulesets, producing a reviewable risk report.

2. North star + Definition of Done  
- North star slice: compliance-lite checker—given cad_semantics + BoQ + plan, output a `cad_risk_report` artifact with rule-based findings (e.g., egress spacing, opening ratios, scope completeness) and severity scores.  
- Definition of Done:  
  - Workers can POST relevant artifact ids and receive a `cad_risk_report` artifact (media_v2) listing `RiskFinding`s with rule_id, severity, impacted elements/tasks, and remediation hints.  
  - Rulesets versioned; meta records rule_version, counts by severity, hash, source ids.  
  - Tests verify rule triggers on fixtures (positive/negative cases) and deterministic ordering/hash; missing data handled with warnings.

3. Scope (In / Out)  
- In: risk rule engine, ruleset definitions, risk artifact registration, service/routes, mapping to elements/tasks.  
- Out: portfolio rollups (next phase), UI/auth/tenant/safety/orchestration/connectors/vector stores/logging changes.

4. Modules to touch (hard allow-list)  
- engines/cad_risk_scoring/models.py  
- engines/cad_risk_scoring/service.py  
- engines/cad_risk_scoring/routes.py  
- engines/cad_risk_scoring/rules.py  
- engines/cad_risk_scoring/tests/test_rules_triggers.py  
- engines/cad_risk_scoring/tests/test_risk_report_meta.py  
- engines/cad_risk_scoring/tests/test_risk_determinism.py  
- engines/cad_semantics/models.py (READ-ONLY unless schema change marked CONTRACT CHANGE)  
- engines/boq_quantities/models.py (READ-ONLY unless schema change marked)  
- engines/boq_costing/models.py (READ-ONLY unless schema change marked)  
- engines/plan_of_work/models.py (READ-ONLY unless schema change marked)  
- engines/media_v2/models.py (only to register cad_risk_report artifact kind/schema)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only for cad_risk_report artifact validation)  
- docs/engines/geometry_cad_program/PHASE_CAD07_risk_and_compliance_P11_P12.md  
- docs/engines/geometry_cad_program/00_MASTER_PLAN_lane_B.md (risk summary only)  
- READ-ONLY context: portfolio modules and docs not listed.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

5. Implementation checklist  
- Design & contracts  
  - Define `RiskFinding` schema (id, rule_id, severity, description, impacted_ids, remediation, calc_version) and `cad_risk_report` artifact meta (rule_version, counts by severity, hash, source ids).  
  - Register artifact kind in media_v2.  
- Rulesets  
  - Implement rules for: egress/door spacing, opening ratios, minimum room areas, slab thickness bounds, missing category coverage (e.g., no finishes), schedule density (tasks/day thresholds).  
  - Allow config overrides per request; record overrides in meta.  
- Service & routes  
  - In service.py: load required artifacts (semantics + BoQ + plan or cost), run rules, collect findings, compute hash, register artifact; support caching by rule_version + overrides + source ids.  
  - In routes.py: POST /cad/risk_report endpoint; RequestContext required but unchanged.  
- Determinism & ordering  
  - Sort findings deterministically; hash the report; ensure repeated runs match.  
- Validation & errors  
  - Handle missing inputs gracefully with warnings; fail fast on incompatible artifact types.  
- Fixtures  
  - Create fixtures with intentional violations (missing exits, undersized rooms) and compliant variants; expected findings/severity documented.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

6. Tests  
- engines/cad_risk_scoring/tests/test_rules_triggers.py: asserts rule triggers on violating fixtures and not on compliant ones.  
- engines/cad_risk_scoring/tests/test_risk_report_meta.py: meta correctness (rule_version, counts, hash) and ordering.  
- engines/cad_risk_scoring/tests/test_risk_determinism.py: same inputs → same findings/hash; cache hit/miss on override changes.  
- engines/media_v2/tests/test_media_v2_endpoints.py: cad_risk_report artifact validation and tenant/env enforcement if applicable.  
- Negative tests: missing inputs warnings vs hard errors; incompatible artifacts rejected.

7. Docs & examples  
- Update this phase doc with rule list, severity definitions, meta fields, override knobs.  
- Update lane_B master plan risk section.  
- Example: POST /cad/ingest → /cad/semantics → /cad/boq_quantities → /cad/boq_cost → /cad/plan_of_work; POST /cad/risk_report → findings/severity summary.

8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If schemas or artifact kinds change, mark CONTRACT CHANGE here and only update the explicitly listed model/test files.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed.

9. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if another file seems required, stop and report. Deliver the full Definition of Done with passing tests, then proceed to PHASE_CAD08 unless blocked by a genuine TODO – HUMAN DECISION REQUIRED.
