# Phase 0.4 — Surface Engines KPI + Temperature Acceptance

Prereqs
- Server running on :8010 with filesystem writable (var/…).
- Surface normalization helper deployed (aliases: squared/squared2/SQUARED2/SQUARED² → canonical squared2).
- Filesystem repos active for KPI and Temperature (no in-memory).

### 1) KPI persistence + aliasing
Write corridor with alias, read with canonical:
```bash
curl -X PUT http://localhost:8010/kpi/corridors \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","kpi_name":"weekly_leads","floor":5,"ceiling":50}'
curl "http://localhost:8010/kpi/corridors?surface=SQUARED²" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect corridor present. Then restart server and re-run GET to confirm durability. File evidence:
```bash
find var/kpi -type f -maxdepth 6 -print | sed 's/^/FILE: /'
```

### 2) Surface KPI Set
```bash
curl "http://localhost:8010/kpi/config?surface=SQUARED²" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' | jq '.surface_kpis'
```
Expect 6 entries for SQUARED²; survives restart.

### 3) Temperature config persistence + aliasing
Write with alias, read with canonical:
```bash
curl -X PUT http://localhost:8010/temperature/floors \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","performance_floors":{"weekly_leads":5},"cadence_floors":{"email_campaigns_per_week":1}}'
curl -X PUT http://localhost:8010/temperature/ceilings \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","ceilings":{"complaint_rate":0.2}}'
curl -X PUT http://localhost:8010/temperature/weights \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","weights":{"weekly_leads":1.0},"source":"tenant_override"}'
curl "http://localhost:8010/temperature/config?surface=SQUARED²" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect floors/ceilings/weights present. Restart and re-run GET. File evidence:
```bash
find var/temperature -type f -maxdepth 6 -print | sed 's/^/FILE: /'
```
Verify weights independence: after weights PUT, confirm floors/ceilings files checksum unchanged (e.g., `shasum var/temperature/.../floors.json var/temperature/.../ceilings.json` before/after).

### 4) Temperature current + GateChain hook
```bash
curl "http://localhost:8010/temperature/current?surface=SQUARED²&window_days=7" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect TemperatureSnapshot with normalized surface and source != in_memory when external adapter present.

### 5) Alias round-trip proof
Write with SQUARED², read with squared:
```bash
curl -X PUT http://localhost:8010/kpi/definitions \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"SQUARED²","name":"returns_rate","unit":"percent"}'
curl "http://localhost:8010/kpi/definitions?surface=squared" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect definition visible; proves alias handling.

### 6) Raw KPI ingestion durability
```bash
curl -X POST http://localhost:8010/kpi/raw \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","app_id":"app1","project_id":"p1","kpi_name":"net_sales","value":12345,"unit":"currency","exact":false,"missing_components":["discounts"],"run_id":"run1","trace_id":"tr1"}'
curl "http://localhost:8010/kpi/raw?surface=SQUARED²" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect entry present; restart server and re-run GET; check file exists under var/kpi/.../raw.jsonl.

### 7) GateChain KPI enforcement (beyond presence)
1. Seed corridor for weekly_leads floor 5; seed raw value 2 → call any GateChain path (e.g., /actions/execute with surface SQUARED²) expecting 403 with detail including kpi_name and value; SAFETY_DECISION shows BLOCK.  
2. Seed raw value 10 (above floor) → same call returns PASS.  
Proof: capture HTTP responses and tail SAFETY_DECISION from timeline or logs.
