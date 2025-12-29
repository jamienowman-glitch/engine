	•	[NOW] Enforce tenant/env + membership on every HTTP route that currently says “no auth enforcement” (timeline, masks, regions, presets, sample_library, scene_engine, bossman, etc.) + add “tenant A can’t read tenant B” tests per router.


	•	[NOW] Add a single Tool Execution wrapper (even before full tool registry) that every callable engine route can go through: StrategyLock (writes) + Firearms (dangerous) + kill-switch + budget meter + DatasetEvent + audit event.


	•	[NOW] Make “prod mode” config fail loud: in-memory repos forbidden for user-facing services unless explicitly APP_ENV=dev, and startup check prints/aborts if persistence backend missing.


	•	[NOW] Unify storage reality: pick canonical raw object storage pathing (S3 per-tenant/per-user) and ensure media_v2 + uploads can write real objects (no local disk) with clear URIs + lifecycle/retention placeholders.


	•	[NOW] Standardize RequestContext/DatasetEvent fields everywhere (tenant_id/env/user_id/surface/app/agent ids where available) and ensure PII strip + train_ok is applied consistently on all event emission paths.

	•	[NOW] Add audit coverage map: which actions emit audit events today vs missing (billing changes, kill-switch writes, strategy lock approvals, firearms license changes, connector ops execution once added).


	•	[NOW] Lock down any remaining “mock/dev auth” routes so they can’t be hit in prod; document exactly how to bootstrap first tenant + invite/membership lifecycle.


	•	[NOW] Tighten Maybes to “raw text only”: ensure saves/forwards store raw message bundles, not summaries; add idempotency + search minimal (by title/tag/text) + retention controls.

	•	[NOW] Memory service: add explicit retention/eviction policy + per-project (chat thread) scoping + “do not leak across tenant” tests; make session-to-session retrieval deterministic (what fields, what query).


	•	[NOW] Bossman dashboard: add generated_at + data_freshness fields per section and make auth/tenant scoping airtight; add at least one dedicated test suite for bossman completeness/scoping.


	•	[NOW] Kill-switches: document + implement where they’re actually enforced today (budget provider block) vs “stored but unused” (disable_autonomy/disabled_actions) and add enforcement hooks at tool-executor boundary.
	•	[NOW] Strategy Lock: ensure it gates every state-changing route it’s meant to gate (you already have many) + require explicit action constants for each write path + add regression tests for 409 behavior.


	•	[NOW] Firearms: define a production license store shape (even if Firestore first) + make every “dangerous” tool/action declare a firearms action constant; add tests that verify denial without license.

	•	[NOW] Billing skeleton: keep Stripe as a connector later, but for now ensure webhook verification, idempotency keys, event replay safety, and tenant mapping are production-safe; add “no double-charge / no duplicate subscription record” tests.

	•	[NOW] BigQuery event sink: define dataset/table naming conventions + partitioning/cluster guidance + add a smoke insert test; ensure backpressure/errors never crash request handlers.

	•	[NOW] Observability: add a correlation id (episode/run id) threaded through RequestContext → tool exec → model call → DatasetEvent so you can debug “what happened” without guessing.

	•	[NOW] Tool registry minimal: define ToolDescriptor schema (id, version, tenant scope, required gates, cost model hooks) and validate “only registered tools callable” in orchestrator/runtime entrypoints.

	•	[NOW] BYOK keys: standardize secret_ref plumbing (GSM-only) without writing secrets yet; ensure every model/tool call resolves via secret_ref and logs provider/model/token usage.

	•	[NOW] Routing (Rootsmanuva): expose as an API + log every decision to EventLog/DatasetEvent; ensure tenant-scoped routing profiles; add tests for deterministic scoring stability.

	•	[NOW] Selecta Loop: wire selector_agent_card_id plumbing + event schemas + schedule hooks (even if cron later) and log selections; no prompts in engines.

	•	[NOW] Grounding/hallucination: define a “grounding required” flag per surface/app (config) + log citation/trace expectations; implement minimal “retrieval trace exists or mark ungrounded” metric.

	•	[NOW] No-prompts sweep: automated repo check that fails CI if prompt-like strings/personas/orchestration logic appear inside /engines (allow docs/tests exceptions as configured).

	•	[DEPENDS] Connectors repo framework: scaffold connector templates/instances/ops catalog schemas + execution stubs that call tool-executor boundary (but do not implement OAuth or store secrets yet).

	•	[DEPENDS] OAuth/BYOK flows: real OAuth requires connector infra + secret storage + callback hosting + consent UI; BYOK requires the same secret_ref infra and tenant-scoped validation UI (you’re building UI).

	•	[DEPENDS] “Everything as tools” UI: requires tool registry + executor so your canvas buttons can call tool ids, not ad-hoc endpoints.

	•	[DEPENDS] WS/SSE realtime: depends on stable auth + tenant scoping + correlation ids so live events can stream safely per tenant/project.

	•	[DEPENDS] Haze terrain/explorer: depends on Nexus classifier/terrain aggregates + usage logs + stable IDs on cards/atoms/packs; FE can come after APIs.

	•	[DEPENDS] Research ingestion agents: depends on connectors repo + policy/robots/copyright stance + safe summarization rules + citations pipeline; keep engines deterministic.

	•	[DEPENDS] KPI/Budget enforcement in orchestration: depends on having orchestration stages + tool-executor enforcement points (otherwise KPI corridors are just config).

	•	[DEPENDS] “Golden rules store” (hard rules not in Nexus): depends on picking a config DB/table (Firestore/BQ/SQL) + APIs + caching; then enforcement lives at tool executor/orchestrator.

	•	[MUSCLE] video_anonymise: needs real face/region backend + perf + auth + persistence + tests before exposure (keep dev-only until then).

	•	[MUSCLE] video_regions/video_visual_meta: replace stub detectors with real backends or clearly label as stub in API + add backend selection/error tests.

	•	[MUSCLE] multicam alignment + align engine: implement real alignment math/backend and add deterministic tests; current stub is fine only for dev scaffolding.

	: fix functional correctness (bone counts etc.) + add stability tests; keep out of core app path until green.
	•	[MUSCLE] audio_hits/loops/phrases: add HTTP surfaces (if you want UI calls) + harden librosa/ffmpeg dependency failures + large-file handling + storage registration in media_v2.

	•	[MUSCLE] audio_field_to_samples/audio_core + CLI ingest tools: either (a) wrap into tenant-aware services writing to media_v2 + object storage, or (b) explicitly quarantine as internal dev tooling with no prod exposure.

	•	[MUSCLE] page_content scraper: add robots/ToS handling mode + rate limits + PII stripping + tenant auth; otherwise keep internal-only.

	•	[MUSCLE] scene_engine persistence: decide whether scenes are first-class assets in media_v2 or separate store; add auth + versioning + large-scene perf guards.

	•	[MUSCLE] media legacy v1: either deprecate behind media_v2 or harden the same auth/persistence rules; don’t let two pipelines drift in prod.

	•	[MUSCLE] ffmpeg/librosa dependency hardening: add startup probes + clearer runtime errors + container build docs so prod doesn’t “work on my laptop” only.
	
	•	[MUSCLE] forecast/eval/creative services: either expose as tools with proper logging/gating or keep internal; right now they’re scaffolds and shouldn’t be treated as prod features.