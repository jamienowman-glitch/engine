# ORCHESTRATION PATTERNS (LLM + RAILS) – PLANNING

Hybrid orchestration model: thin rails + LLM orchestrator-as-agent. Planning-only; no runtime wiring here.

## Model
- Rails owns scheduling, state machine, guardrail enforcement, and persistence.
- Orchestrator (LLM) decides which cluster/tool to call next within the rails-defined budget and capabilities.

## Rails layer (deterministic)
- Triggers: scheduled (cron), reactive DatasetEvents, manual/backfill; dedupe by `request_id`.
- Lifecycle: Draft → QA → Approved → Published (configurable per surface) with TTL per stage and dead-letter for stuck jobs.
- Limits: per-stage retries/backoff, overall max loops, circuit breakers when repeated guardrail failures occur.
- Enforcement: firearms licences, Strategy Lock, 3-Wise, HITL, KPI/budget corridors before unsafe actions (publish/email/post).
- Logging: every transition and guardrail decision emits DatasetEvents with `manifest_id`, `request_id`, `cluster_id` (if present).

## Orchestrator-as-agent (LLM)
- Inputs: blackboard state, Nexus history, tenant preferences, temperature band, Tool Registry, and cluster capabilities (allowed_reads/writes/ops).
- Chooses which cluster/tool to call next, when to stop, and when to request QA; uses only registered tools whose capabilities allow the desired paths.
- Outputs: structured tool calls and manifest/blackboard patches; no freeform prompts that bypass registry/capabilities.
- Rails validates every proposed patch/op against capabilities before apply; orchestrator cannot self-apply writes.

## Hook points to existing engines
- Temperature: influences strategy selection (content vs sales emphasis) but never overrides firearms rules.
- Strategy Lock + 3-Wise: invoked pre/post risky actions; gates auto-action vs HITL.
- Firearms/HITL: required for outbound or destructive actions; rails blocks publish/send until cleared.
- Logging: all orchestration steps emit DatasetEvents for audit/analytics.

## Use-case example (blog from YouTube event)
1) DatasetEvent `content.published.youtube_video` arrives → rails creates Draft job with `request_id`.
2) Rails fetches manifest snapshot + blackboard context limited to `allowed_reads`; sets retry/backoff counters.
3) Orchestrator reads context + temperature band; selects headline cluster → proposes patch `content_slots.hero_headline.text`.
4) Rails validates `path/op` vs capabilities, applies patch, and emits DatasetEvent `orchestration.patch_applied`.
5) Orchestrator calls body cluster then meta/SEO cluster; rails enforces per-cluster retries and logs outputs.
6) QA cluster runs; outputs QA report to blackboard; if fail, rails loops (bounded) or dead-letters with reason.
7) Before publish/email, rails runs firearms/Strategy Lock/3-Wise/HITL gates; if any block, state stays in QA with TODO recorded.
8) On clearance, rails transitions Approved → Published and emits `orchestration.published` plus downstream triggers (e.g., connector push).
9) All steps logged; no direct token writes outside allowed paths; drafts remain in blackboard if publish blocked.

## Non-goals (this pass)
- No new endpoints or services.
- No routing/agent code; only contracts and patterns for future implementation.
