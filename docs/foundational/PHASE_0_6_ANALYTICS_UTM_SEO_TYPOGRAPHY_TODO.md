# Phase 0.6 — Analytics + UTM + SEO/AEO + Typography/Variable Fonts (Docs-Only TODO)

Goal: make analytics/UTM/SEO tracking durable and tenant/mode/surface/app scoped; ensure internal UTMs captured; add measurement hooks for SEO/AEO; tighten typography/variable fonts registry and controls. No rebuilds; wire existing modules. Engines-first, then UI, then muscle wiring.

## Lane Plan (checkboxes)
- [ ] Lane 0 — Scope + normalization (context + surface)
  - Apply surface/request context normalization to analytics/seo routes and any new tracking endpoints; preserve tenant/mode/project/surface/app/user/request_id.
  - DoD: all analytics/seo routes accept aliases (incl. SQUARED²) and store canonical surface; headers enforced.

- [ ] Lane 1 — Analytics events durability (engines)
  - Files: engines/analytics_events/{models,repository,service,routes}.py.
  - Replace env-driven in-memory defaults with filesystem (baseline) and optional Firestore; ensure record includes tenant/mode/project/app/surface/user/session if available.
  - Emit StreamEvent/Audit on route changes/ingest; stop swallowing GateChain errors silently (configurable).
  - DoD: POST /analytics/events/pageview|cta-click persisted (file evidence), replayable/queriable, scoped keys present.

- [ ] Lane 2 — Internal UTM capture + builder hooks (UI + engines boundary)
  - Add UTM builder/decorator in UI transport/router for internal nav; propagate UTMs in requests to engines analytics endpoints.
  - Engines: ensure UTMs stored on AnalyticsEventRecord (models already have utm_* fields).
  - DoD: internal nav links include UTMs; POSTed events contain UTMs; persisted record shows them.

- [ ] Lane 3 — SEO/AEO persistence + measurement
  - Files: engines/seo/{models,repository,service,routes}.py; engines/analytics_events for engagement; optional new routes for schema/landing measurements.
  - Ensure SEO repo durable (filesystem baseline), scoped by tenant/mode/surface/page_type; add AEO structured data storage if missing.
  - Add measurement hooks (landing/conversion/engagement) via analytics_events or new endpoint, persisted with scope.
  - DoD: PUT/GET SEO config persists; measurement events stored with SEO context (slug/title/description).

- [ ] Lane 4 — UI analytics/SEO wiring
  - Update UI transport wrappers to send required headers + UTMs; add client-side hook to call analytics endpoints; ensure no PII leakage.
  - DoD: UI fires pageview/cta events with UTMs and scope; respects Authorization; works with Last-Event-ID replay unchanged.

- [ ] Lane 5 — Typography/Variable Fonts hardening
  - Files: engines/design/fonts/registry.py + font JSONs; engines/typography_core/*; muscle renderers consuming typography; UI components if present.
  - Ensure variable font axes exposed (wght/wdth/slnt/opsz/etc) and presets registry-driven; allow adding new font via data (JSON + asset).
  - Add per-letter styling/case/kerning controls path if missing; confirm fontVariationSettings emitted to CSS/renderer.
  - DoD: new font added without code change; test confirms variation axes render; letter-level control reachable.

- [ ] Lane 6 — AEO/SEO measurements to agents (queryability)
  - Add read/list routes for analytics events/SEO configs scoped by tenant/mode/surface/app/project; ensure agents can fetch (no GA-only).
  - DoD: GET analytics events returns stored records; includes scope+UTM+SEO fields.

- [ ] Lane 7 — Tests + acceptance updates
  - Add filesystem persistence tests for analytics/seo; alias tests; typography variation tests.
  - DoD: test suite covers persistence, UTMs, variation settings; doc acceptance passes.

## Do-not-break invariants
- No env-driven backend selection (except creds); filesystem baseline.
- No monolith configs; keep modules separate (analytics vs seo vs typography).
- No “one router” orchestrator; boundaries stay thin.
- GateChain behavior unchanged (only telemetry paths may gate/skip).

