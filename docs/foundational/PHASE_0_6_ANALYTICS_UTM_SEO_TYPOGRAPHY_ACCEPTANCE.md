# Phase 0.6 — Analytics/UTM/SEO/Typo Acceptance

Prereqs: filesystem writable; analytics/seo repos set to filesystem; surface normalizer present (aliases squared/squared2/SQUARED2/SQUARED² → canonical).

## Analytics events durability + UTMs
```bash
curl -X POST http://localhost:8010/analytics/events/pageview \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"surface":"squared","url":"https://app/page","utm_source":"internal","utm_medium":"nav","utm_campaign":"home-nav","metadata":{"test":1}}'
curl "http://localhost:8010/analytics/events?page=1&limit=10" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect persisted record with UTMs; restart and list returns it; file evidence under var/analytics_events/…

## CTA + alias round-trip
```bash
curl -X POST http://localhost:8010/analytics/events/cta-click \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"surface":"SQUARED²","cta_id":"cta123","label":"Buy","utm_source":"internal","utm_medium":"cta","utm_campaign":"home"}'
curl "http://localhost:8010/analytics/events?surface=squared" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect event visible; proves alias handling.

## SEO config durability
```bash
curl -X PUT http://localhost:8010/seo/pages \
  -H 'Content-Type: application/json' \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1' \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","page_type":"home","title":"Home","description":"Welcome","canonical_url":"https://example.com"}'
curl "http://localhost:8010/seo/pages?surface=SQUARED²" \
  -H 'X-Mode: saas' -H 'X-Tenant-Id: t_demo' -H 'X-Project-Id: p1'
```
Expect config persisted; restart and GET returns; file exists under var/seo/…

## AEO/measurement hook
Trigger landing/engagement event (route TBD if added) with SEO context and verify stored record includes seo_slug/title/description.

## Typography/variable fonts
1) List fonts via registry (CLI/test) to show variable font (e.g., Roboto Flex) loaded.  
2) Render/layout call (test) asserting `fontVariationSettings` includes axes (wght/…); overrides applied.  
3) Add new font JSON + asset, run render without code change to confirm data-only addition.

## Internal UTM propagation (UI)
Using UI build, navigate internal link and verify emitted analytics payload contains UTMs (inspect network or mocked endpoint).

## Stream/Audit on analytics config change
If analytics/seo routing/config is changed, check audit log or StreamEvent for action=routing.upsert or config change including scope.
