# Phase 0.6 — Attribution + Analytics + Variable Fonts (Engines-only TODO)

Hard rules: routing registry selects backends (no env-driven); sellable modes (t_system/enterprise/saas) must use cloud backends; filesystem/in-memory allowed only in lab; no UI build; env removed from scoping (mode/project/app/surface instead); GateChain errors not swallowed.

## Lane Plan (checkboxes)
- [ ] Lane A: AttributionContractV1 (tabular_store via routing)
  - Files: engines/analytics_events (or new attribution module) models/service/routes; routing registry resource_kind (tabular_store or attribution_store).
  - Schema: tenant_id, mode, project_id, platform (required), utm_template, allowed_fields, attach_rules, version/meta.
  - DoD: GET/PUT contract persists via routing-selected backend; cloud-only in sellable modes; lab can use filesystem; route change auditable.
  - Acceptance: PUT contract -> GET returns after restart; route flip proof; forbidden_backend_class when mode=saas and backend=filesystem.

- [ ] Lane B: /attribution/tag_link endpoint
  - Files: attribution routes/service.
  - Behavior: input platform, destination_url, fields; output tagged_url, contract_version_used, warnings.
  - DoD: Uses stored contract; rejects if contract missing; respects routing guard.
  - Acceptance: POST tag_link returns tagged URL; restart and contract persists.

- [ ] Lane C: Analytics ingestion durable + scoped + queryable
  - Files: engines/analytics_events/{models,service,repository,routes}.py.
  - Persist required fields: tenant_id, mode, project_id, platform (required), session_id (required), request_id (required), utm_*, landing/current/referrer/previous_url; optional app_id/surface_id/user_id/run_id/step_id; ingest_status/gate_error on GateChain failure.
  - Backend selection via routing (analytics_store or metrics_store); remove in-memory/env defaults; cloud-only in sellable modes.
  - Add read/list endpoints with filters (tenant/mode/project/platform/session/time).
  - DoD: ingest persists across restart; query returns data; no silent GateChain swallow (persist with status).
  - Acceptance: ingest 5 events, restart, query returns 5; force gate error → event stored with gate_status=error.

- [ ] Lane D: UTM/internal navigation event types
  - Event types: pageview, cta_click, nav_click; store landing_page, referrer, current_url, previous_url, utm_*, link_id (optional).
  - DoD: sequence of pageview/nav_click/pageview reconstructable per session in stored data.
  - Acceptance: ingest sequence, query by session shows ordered movement.

- [ ] Lane E: Per-letter variable font capability
  - Files: engines/design/fonts (models/registry), typography renderers (engines/typography_core or relevant), atoms_factory contract note (per-letter token shape).
  - Define PerLetterStyleV1 token (grapheme-safe map) and apply in renderer (span per grapheme with font-variation settings).
  - DoD: renderer test proves per-letter variations applied; no UI required.
  - Acceptance: snapshot/computed style test for per-letter overrides.

- [ ] Lane F: Multi-font ingestion pipeline (beyond Roboto Flex)
  - Files: engines/design/fonts registry/presets; add ingestion path to register variable fonts + presets (TSV) via routing-selected object_store/tabular_store.
  - DoD: new font+presets can be added without code change; stored via routing (cloud in sellable modes); list/read endpoints for fonts/presets.
  - Acceptance: add second font fixture, list shows it with presets after restart.

- [ ] Lane G: SEO scope correction (no build)
  - Files: engines/seo models/service/repo/routes.
  - Update scoping to tenant_id + mode + project_id (+ app_id/surface_id if used); deprecate env; keep backwards-compatible reads if needed.
  - DoD: PUT/GET scoped correctly; persistence via routing (tabular_store).
  - Acceptance: write/read SEO config with mode/project; restart proof.

- [ ] Lane H: GateChain handling for analytics
  - Files: engines/analytics_events/service.py.
  - On GateChain failure, persist event with ingest_status=accepted_with_gate_error + gate_error_code/reason; return explicit status; no drops.
  - DoD: gate error traceable; event not lost.
  - Acceptance: force gate error and verify stored status.

## Do-not-break invariants
- No env-driven backend selection; no in-memory defaults in sellable modes.
- Filesystem/local backends allowed only in lab; routing guard enforces backend_class=cloud for sellable modes.
- No monolith configs; adapters per domain; routing registry central.
- No UI/agents edits except AGENTS.md in agent-factory repo.
