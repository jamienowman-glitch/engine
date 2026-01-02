# Phase 0.4 — Surface Engines (KPI + Temperature) TODO

Goal: make KPI and Temperature subsystems durable and surface-generic (filesystem default, optional Firestore later), add surface normalization with SQUARED² aliases, seed SQUARED² configs (data-only), and keep GateChain compatibility. No refactors, no monoliths, no env-driven thresholds.

Glossary/locked tokens (no undefined abbreviations): Rolling 7D/14D/30D/365D; MTD/WTD/YTD/FYTD; Today (Live), Yesterday (Closed); Launch To Date (LTD), Launch +7D/+14D/+30D, Campaign Start→End; comparisons: YoY, vs Target, Δ, %. Temperature bands: Ice 0–40, Blue 40–55, Yellow 55–65, Green 65–75, Yellow 75–90, Red 90–100. Smoothing term only (default Rolling 7D).

## Lane Plan (checkboxes)
- [ ] Lane 0: Surface normalization helper (generic)
  - Files: engines/common/surface_normalizer.py (new); apply in engines/kpi/service.py, engines/kpi/routes.py, engines/temperature/service.py, engines/temperature/routes.py, engines/nexus/hardening/gate_chain.py callers if needed.
  - Scope: normalize incoming surface strings to canonical ASCII id; alias table (squared, squared2, SQUARED2, SQUARED² → squared2 internal; display label SQUARED²). Reusable for future surfaces.
  - DoD: PUT/GET on KPI/Temperature accept any alias and store/read canonical; GateChain uses normalized surface; tests updated to assert alias behavior.

- [ ] Lane 1: KPI durable persistence (filesystem default)
  - Files: engines/kpi/repository.py (add FileKpiRepository), engines/kpi/service.py (select file repo by default; no env-driven fallback in real infra), engines/kpi/routes.py (no behavior change), tests to cover persistence.
  - Layout: var/kpi/{tenant}/{mode_or_env}/{surface}/definitions.jsonl, corridors.jsonl, surface_kpis.json (see Lane 3). Separate files for definitions vs corridors vs surface KPI set.
  - DoD: definitions/corridors/surface_kpis survive restart on filesystem; Firestore stub optional only; GateChain reads corridors from file store.

- [ ] Lane 2: Temperature durable persistence (filesystem default)
  - Files: engines/temperature/repository.py (add FileTemperatureRepository), engines/temperature/service.py (select file repo by default; keep adapters pluggable), engines/temperature/routes.py (no monolith config).
  - Layout: var/temperature/{tenant}/{mode_or_env}/{surface}/floors.json, ceilings.json, weights.json, snapshots.jsonl. Floors/ceilings/weights separate files/objects; weights independent from floors/ceilings.
  - DoD: floors/ceilings/weights persist independently; GET /temperature/config/current works after restart; GateChain uses normalized surface; updating weights does not overwrite floors/ceilings files.

- [ ] Lane 3: Surface KPI Set config (generic + seed SQUARED²)
  - Files: engines/kpi/models.py (add SurfaceKpiSet model), engines/kpi/repository.py/service.py/routes.py (CRUD/read with surface scope), seed fixture/config file for SQUARED² defaults (no code special-case).
  - Surface KPI set requirements (config fields): name, description/calc, window token (from glossary), comparison token (optional), flags for ESTIMATE and missing_components list, display label, notes. Seed 6-core KPIs for SQUARED² (below). Stored separately from corridors.
  - DoD: GET /kpi/config returns {definitions, corridors, surface_kpis} including seeded SQUARED² list; persists on filesystem; alias read/write works.

- [ ] Lane 4: Raw KPI ingestion store (filesystem baseline)
  - Files: engines/kpi/repository.py/service.py/routes.py (new raw ingestion path); storage under var/kpi/{tenant}/{mode_or_env}/{surface}/raw.jsonl or similar; structured records per tenant/surface/app/project/run/trace; flag exact vs ESTIMATE + missing_fields list.
  - DoD: POST raw KPI measurement persists and survives restart; not routed through Nexus; supports alias surfaces.

- [ ] Lane 5: Seed SQUARED² data (config-only)
  - Files: data/seed/surfaces/squared2/kpi.json, temperature.json (or similar minimal seed loader); wiring in startup seed script if present (or documented curl steps).
  - DoD: After seed, GET /kpi/config?surface=SQUARED² and /temperature/config?surface=SQUARED² return seeded defaults; alias read/write works.

- [ ] Lane 6: GateChain KPI enforcement upgrade
  - Files: engines/nexus/hardening/gate_chain.py, engines/kpi/service.py (add value lookup), KPI raw ingestion store.
  - DoD: GateChain evaluates current/derived KPI values against corridors (not presence-only); blocks when out-of-bounds; uses normalized surface; SAFETY_DECISION includes kpi_name and value.

- [ ] Lane 7: Tests + alias migration
  - Files: engines/kpi/tests/*, engines/temperature/tests/*, any “squared” literals → exercise alias normalization rather than hardcoded string; new persistence tests (definitions/corridors/surface_kpis/raw, floors/ceilings/weights).
  - DoD: tests pass using canonical helper; all pass.

## Do-not-break invariants
- No env-driven thresholds or repo selection in real runs; filesystem default for durability.
- No monolith configs; floors/ceilings/weights stay separate; surface KPI set stays separate from corridors.
- No new orchestrators; boundaries stay thin.
- Keep existing GateChain behavior; only add normalization/persistence beneath it.

## Acceptance checks (per Lane)
- Lane 0: POST /kpi/definitions with surface=squared returns under normalized surface; GET with surface=SQUARED² returns same record; tests cover alias helper.
- Lane 1: Restart server; GET /kpi/corridors returns previously written corridor (file exists under var/kpi/...); surface_kpis stored separately; filesystem evidence present.
- Lane 2: Restart server; GET /temperature/config returns previously written floors/ceilings/weights; files exist under var/temperature/... split per type; updating weights does not change floors/ceilings files.
- Lane 3: GET /kpi/config?surface=SQUARED² returns seeded surface_kpis list (6 entries) and any seeded corridors/definitions; alias squared also works.
- Lane 4: POST raw KPI measurement persists and survives restart; retrieve raw entry via GET; alias handling works.
- Lane 5: GateChain blocks when KPI value exceeds corridor, SAFETY_DECISION includes kpi_name and value; uses normalized surface.
- Lane 6: Tests updated to use normalization helper; persistence tests pass.

## Surface KPI set — locked seed (generic fields)
- Profit After Costs (Before Tax): Net Sales − Minimum Included Costs; Net Sales = sales after discounts/returns, before tax; costs include (when connected) COGS, total marketing spend, payment processing fees, platform fees, shipping/fulfilment; if missing inputs mark ESTIMATE + missing_components list; no VAT/corp tax logic.
- MER: Net Sales ÷ Total Marketing Spend (paid media, influencer/creator spend, agency fees if imported); if spend missing mark ESTIMATE + missing list.
- Growth: YoY change in Profit After Costs (Before Tax); fallback secondary view YoY Net Sales when profit is ESTIMATE/incomplete.
- Discount Rate: Total Discounts ÷ Gross Sales (pre-discount, pre-tax; discounts include promo/auto/markdowns/bundles).
- Returns Rate: Returned Units (received/confirmed) ÷ Sold Units; if only requested exists compute but mark ESTIMATE until received exists.
- AOA: Unique reachable owned-channel people engaged ≥1 in last 90D (open/click/reply/react/recognized visit/community); 90D default knob.
- Each KPI config carries: name, description/calc, window token, comparison token (optional), estimate flag, missing_components list, display label, notes.
