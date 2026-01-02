# Phase 0.4 — Surface Engines KPI + Temperature Seed

## SQUARED² KPI set
`data/seed/surfaces/squared2/kpi.json` holds the canonical SurfaceKpiSet for the SQUARED² alias family. The file names the six locked KPIs (Profit After Costs, MER, Growth, Discount Rate, Returns Rate, AOA) along with their descriptions, window/comparison tokens, estimate flags, and missing component guidance.

To seed the set:
```bash
curl -X PUT http://localhost:8010/kpi/surface-kpis \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p_demo' \
  -d @data/seed/surfaces/squared2/kpi.json
```
After the request, `GET /kpi/config?surface=SQUARED²` should expose the same list under `surface_kpis` and the canonical surface name `squared2`.

## SQUARED² Temperature configuration
`data/seed/surfaces/squared2/temperature.json` documents one set of floors, ceilings, and weights for the same tenant/surface scope. Use the respective sections when writing each config:
```bash
jq -c '.floors' data/seed/surfaces/squared2/temperature.json \
  | curl -X PUT http://localhost:8010/temperature/floors \
    -H 'Content-Type: application/json' \
    -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p_demo' \
    -d @-

jq -c '.ceilings' data/seed/surfaces/squared2/temperature.json \
  | curl -X PUT http://localhost:8010/temperature/ceilings \
    -H 'Content-Type: application/json' \
    -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p_demo' \
    -d @-

jq -c '.weights' data/seed/surfaces/squared2/temperature.json \
  | curl -X PUT http://localhost:8010/temperature/weights \
    -H 'Content-Type: application/json' \
    -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p_demo' \
    -d @-
```
After seeding, `GET /temperature/config?surface=SQUARED²` should include the same floors/ceilings/weights, and the filesystem-backed repo will persist them under `var/temperature/t_demo/dev/squared2`.

## Usage notes
- Replace tenant/project/app IDs with the intended environment (the JSON files use `t_demo/p_demo` as placeholders).
- The KPI entries assume canonical `surface` identifier `squared2`; the new surface normalizer accepts the alias (SQUARED²) when seeding and reading.
- These files are data-only reference material; update them if the locked KPIs or temperature thresholds change, then reapply the curl commands.
