# Phase 0.6 — Attribution/Analytics Acceptance

Prereqs: routing registry present; backends configured; sellable modes (saas/enterprise/t_system) use cloud backends; lab may use filesystem; surface normalizer available.

## AttributionContractV1
```bash
curl -X PUT http://localhost:8010/attribution/contract \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"t_demo","mode":"saas","project_id":"p1","platform":"web","utm_template":"utm_source={source}&utm_medium={medium}&utm_campaign={campaign}","allowed_fields":["source","medium","campaign","content","term"],"attach_rules":{"internal":"allow"},"version":"v1"}'
curl "http://localhost:8010/attribution/contract?tenant_id=t_demo&mode=saas&project_id=p1&platform=web"
```
Expect persistence across restart via routing-selected backend; with backend=filesystem and mode=saas, expect forbidden_backend_class error.

## Tag link endpoint
```bash
curl -X POST http://localhost:8010/attribution/tag_link \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"t_demo","mode":"saas","project_id":"p1","platform":"web","destination_url":"https://example.com/page","fields":{"source":"internal","medium":"nav","campaign":"home"}}'
```
Expect tagged_url returned with contract_version_used; fails if contract missing.

## Analytics ingest durability + scope
```bash
curl -X POST http://localhost:8010/analytics/events/pageview \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"t_demo","mode":"saas","project_id":"p1","platform":"web","session_id":"sess1","request_id":"req1","surface_id":"surf1","app_id":"app1","user_id":"u1","utm_source":"internal","utm_medium":"nav","utm_campaign":"home","landing_url":"https://example.com","current_url":"https://example.com/page","referrer":"https://example.com","previous_url":null}'
curl "http://localhost:8010/analytics/events?tenant_id=t_demo&mode=saas&project_id=p1&platform=web&session_id=sess1"
```
Expect event persisted and returned after restart; stored fields include platform/session/utm/current/referrer. With backend=filesystem and mode=saas, expect forbidden_backend_class.

GateChain error path: configure gate to fail, POST event, expect response status showing gate_status=error and event visible in query with gate_error fields.

## Internal navigation reconstruction
1) pageview A (landing_url=https://a) session_id=sess2  
2) nav_click to B (current_url=https://b, previous_url=https://a)  
3) pageview B (current_url=https://b, previous_url=https://a)  
Query session sess2 returns ordered events to reconstruct movement.

## Filesystem vs cloud guard
- Route analytics_store to filesystem, send event with mode=lab → succeeds and file exists.
- Same with mode=saas → fails with forbidden_backend_class.

## Per-letter rendering test
- Run typography renderer test that applies PerLetterStyleV1 overrides; assert computed font-variation-settings differ per grapheme (snapshot or CSS tokens).

## Multi-font ingestion
- Upload/register second variable font + TSV presets via object_store/tabular_store routes; list fonts/presets endpoint returns new font after restart.
