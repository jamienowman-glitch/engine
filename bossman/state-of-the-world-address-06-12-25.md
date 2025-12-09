# State of the World Address – 2025-12-06

Scope: northstar-engines backend (with notes on core/connector dependencies). Focused on what exists, how it behaves, and what must be hardened to hit v0.

## Surfaces → Apps → Federations → Clusters → Agents
- References: cards/plan docs (PLAN-023), constitution docs (MANIFEST_TOKEN_GRAPH.md, CLUSTER_CAPABILITIES.md, DESIGN_TOOLS_SCOPING.md), plan entries in docs/02_REPO_PLAN.md.
- Current state: shapes and constraints documented; card-driven hierarchy acknowledged; no hard-coded enums. Engines know about surfaces/agents conceptually via cards, not runtime enforcement.
- Gaps/hardening: ensure all runtime calls consume card IDs (surface/app/federation/cluster/agent), enforce tenant scoping, and expose list/read APIs for these cards. Need manifest/token graph wiring in core to keep hierarchy non-deterministic and card-driven.

## Tools
- References: TOOL_REGISTRY.md, card/manifest notes. Engines expose functions; tools expected to be registered via cards/registry.
- Current state: Tool descriptor schema planned; engines callable as tools; connectors as tools is documented.
- Gaps/hardening: build unified tool registry service + card types; enforce tool_id use across orchestrators; add runtime validation that only registered tools are callable; ensure Firearms metadata attached to tool descriptors.

## Rootsmanuva (routing)
- References: B-ROUTE section in docs/02_REPO_PLAN.md; engines/routing/schemas.py; engines/rootsmanuva_engine.
- Current state: Deterministic routing engine implemented (routing models, scoring, tests). No connectors/LLMs needed. Metric catalogue shape defined.
- Hardening: hook into logging/Episode/EventLog; wire to budget/eval/safety metric feeds when connectors land; expose core API for routing decisions.

## Selecta Loop
- References: B-ROUTE; SelectaLoopService stub.
- Current state: Interface defined; events planned; no LLM prompts embedded.
- Hardening: wire to selector_agent_card_id, add EventLog schemas, schedule periodic runs; integrate with routing profiles lifecycle.

## Grounding & hallucinations
- References: 3-Wise, guardrails docs (FIREARMS_AND_HITL.md), safety adapters.
- Current state: 3-Wise concept planned; guardrail adapter combines vendor guardrails + Firearms/3-Wise; no dedicated grounding service.
- Hardening: add retrieval-augmented checks, reference tracing, and hallucination detectors; define policy for grounding per surface; add eval metrics for hallucination rate.

## Strategy Lock
- References: STRATEGY_LOCK_ACTIONS.md, plan docs.
- Current state: Human-in-loop checkpoint after KPI/Budget/Firearms/3-Wise; documented, not fully enforced in runtime.
- Hardening: add mandatory orchestration stage with HITL requirement; log decisions; enforce before publish/actions.

## Policies & Rules
- References: FIREARMS_AND_HITL.md, planning notes (B-POLICY).
- Current state: Rules live in docs/plans; Nexus explicitly not for hard rules.
- Hardening: define tables/config store (e.g., relational/BigQuery) for tenant rules; add fetch APIs; migrate any future hard rules out of Nexus; add policy cache and enforcement points.

## 3-Wise LLM
- References: docs/constitution, strategy lock/3-Wise planning.
- Current state: Conceptual; no prompts; guarded to be card-driven.
- Hardening: implement orchestration hook that fans out to 3 agents/models configured via cards; log ModelCall/PromptSnapshot; ensure prompts come from cards; allow Rootsmanuva to pick models.

## Firearms Licenses
- References: FIREARMS_AND_HITL.md, guardrail adapter.
- Current state: Policy documented; adapter supports Firearms verdicts; no license store implemented.
- Hardening: define license schema (table/config), attach to tools/actions; enforce in guardrail adapter; audit paths with ADK agent identity once connectors allow first-class agent auth.

## Floors & Ceilings (KPI/Budget corridors)
- References: Budget Watcher planning, KPI corridors in control/state schemas.
- Current state: UsageMetric/CostRecord schemas exist; BudgetService decisions; temperature/KPI corridors documented.
- Hardening: implement corridor enforcement in orchestrator stages; aggregate usage; block/slow paths when ceilings hit; uplift when below floors; add logging to OrchestrationStage.

## KPI
- References: control/state schemas (KpiCorridor), plan docs.
- Current state: KPI corridors schema; temperature engine references KPIs.
- Hardening: expose KPI CRUD; ensure orchestrators consult KPI corridors; add logging of KPI deltas per Episode.

## Budgets
- References: Budget Watcher planning; UsageMetric/CostRecord models.
- Current state: Models + decision service; AWS CUR ingest planned but waiting on connectors.
- Hardening: implement ingestion (Vertex/Bedrock/CUR), enforce in orchestrators, surface budget status to Strategy Lock/Firearms/3-Wise; expose user-facing budget status.

## Autonomy
- Current state: Safety/guardrails/strategy lock documented; routing deterministic; HITL hooks exist.
- Gaps: need policy store, budget/KPI enforcement, grounding checks, and license enforcement to safely allow autonomy; add simulation/sandbox modes.

## Lead the Dance
- Current state: Not formalized; implied by manifest/cards and agents querying user.
- Hardening: define “lead the dance” guideline in cards; add orchestration rule to prompt agents to ask for missing context before execution; log “clarify” prompts; add default UX cues.

## Atoms Fam (targeted tokens)
- References: DESIGN_TOOLS_SCOPING, UI builder plans.
- Current state: Conceptual; applies to UI atoms and scoped agents; manifests/token graph doc.
- Hardening: enforce token scopes per agent/tool; log token edits; add per-token permissions in cards.

## Nexus (vector spaces / Haze)
- References: Nexus vector/RAG planning; Haze notion; Nexus shapes implemented (Firestore backend + Vertex vector store).
- Current state: NexusDocument/Embedding/Usage models; RAG service; Vertex vector backend; classifier/terrain planned; no Haze FE yet.
- Hardening: add classifier step, terrain aggregates, Haze APIs; async vector ingestion; ensure no hard rules in Nexus; add upload/mirroring flows only.

## Forecasting
- References: ForecastService schemas/plan (Vertex/BQ ML/AWS).
- Current state: Forecast models/service stubs with tests; config getters added.
- Hardening: connect to real backends; store forecasts; wire alerts to KPI/Budget/temperature loops.

## Tuning
- References: Bot Better Know; eval metrics planning.
- Current state: Limited to BBK; eval service scaffolding.
- Hardening: broaden eval hooks across agents; store eval metrics; use in Rootsmanuva metrics.

## Temperature
- References: control/state + temperature plans.
- Current state: Temperature engine uses plans; macro temperature value surfaced to UI header; KPI/Budget influence planned.
- Hardening: ensure consistent calculation across surfaces; log temp changes to Episodes; expose API.

## Meta-pidgen + Gossip
- Current state: Concept only; no implementation.
- Hardening: define gossip packet schema; pub/sub channel; subscribe hooks for agents; ensure PII-free.

## Blackboards
- References: chat pipeline, Episodes/Nexus logging.
- Current state: Chat persists snippets to Nexus/Firestore; blackboard concept in plans.
- Hardening: define blackboard schema in core; ensure per-episode state accessible; eviction/retention rules.

## Multi-tenant
- References: TENANTS_AUTH_BYOK, runtime_config, Nexus backend tenant separation.
- Current state: Tenant_id in schemas; Firestore collections per tenant; BYOK naming patterns.
- Hardening: enforce tenant isolation at API gateway; per-tenant secrets resolved via connectors; add tenancy checks in routing/budget/safety paths.

## Research → Populate Nexus
- Current state: No automated research agents; Nexus ingestion exists.
- Hardening: plan research pipelines/agents to ingest academic/docs; add classifiers; ensure PII/safety filters.

## Fireprompt (prompt optimisation)
- Current state: Not implemented; only conceptual guidance.
- Hardening: define Fireprompt service (prompt evals, A/B), tie to eval metrics, HITL callable function.

## MDMAD (long-plan execution assistant)
- Current state: New concept; no implementation.
- Hardening: model after Fireprompt: plan templates, risk checks, HITL hooks, Rootsmanuva for tool/agent selection.

## Orchestration
- References: ORCHESTRATION_PATTERNS.md; B-ROUTE; agent runtime adapters.
- Current state: Agent runtime adapters (ADK/Bedrock/LangGraph) planned/partially implemented; routing engine ready; orchestration patterns documented.
- Hardening: implement orchestration stages with logging; enable hybrid deterministic + LLM rails; add trace normalization for Bedrock.

## Agent memory
- Current state: Chat writes to Nexus/Firestore; Episodes; blackboard notion.
- Hardening: explicit memory service; retrieval hooks per agent; retention policies.

## Maybes (human scratchpad)
- References: B-MAYBES section.
- Current state: Planning done; not implemented yet.
- Hardening: implement model/service/APIs/logging; ensure asset_type="maybes_note"; no default Nexus mirroring.

## Haze (3D vector explorer)
- Current state: Scene engine live for scene JSON; Nexus terrain planning; Haze FE not built.
- Hardening: terrain API + usage aggregates; FE to render; hook to Nexus docs.

## Engines (proprietary services)
- Current state: Scene engine, audio/text/media engines implemented; Rootsmanuva engine added.
- Hardening: continue adding engines where third-party not desired; ensure logging/tests/docs up to date.

## Emergence
- Current state: Safety rails planned; routing deterministic; autonomy guarded.
- Hardening: ensure policies/budgets/grounding in place so emergent behavior is safe; add simulation/sandbox to observe emergence.

## Quantum
- References: Creative/QPU hooks planning; Braket notes.
- Current state: QPU schemas/services planned; Braket integration pending connectors.
- Hardening: define datasets and policy for quantum jobs; add Braket adapter once creds available; enforce Firearms/HITL.

## Cards (natural language control)
- Current state: Manifests/cards central in docs; routing profiles are cards; tool descriptors planned; no hardcoded prompts.
- Hardening: ensure all behaviors (3-Wise, Fireprompt, orchestration) sourced from cards; audit for any static prompts; add card registry APIs.

## Personalisation
- Current state: Per-tenant BYOK, token graph allows scopes; no per-agent persona storage yet.
- Hardening: add card fields for communication style/persona; enforce in agent runtime; keep separation between persona vs work product rules.

## Audit / Logs / Tuning / Debugging
- Current state: EventLog engine with PII strip; Nexus logging; ModelCall/PromptSnapshot logging planned; tests present for logging engine.
- Hardening: extend logging to routing decisions, budget hits, guardrail verdicts, selection events; add auditing views; ensure token logs present; add replay/simulation hooks.

## Orchestration pattern inspection
- Current state: Orchestration patterns doc; trace normalization planned; Agent Flow Viewer plan exists.
- Hardening: implement normalized traces across runtimes; build inspection surface; allow simulation of card changes.

## Chat / Realtime transport
- References: chat pipeline, SSE/WS vision in brief.
- Current state: Chat pipeline with LLM hook, Nexus logging; SSE/WS not fully wired; basic tests.
- Hardening: implement WebSocket + SSE split for chat/canvas; add statuses (thinking/planning); ensure orchestration routing per surface/app; multi-tenant auth.

## Tez (internal currency)
- Current state: Concept only.
- Hardening: define Tez ledger schema, earning/spend rules for agents, safety around bidding; consider sandbox isolation.

## RL & RLHA
- Current state: Strategy Lock as RLHA analogue; KPI/Budget corridors for reward shaping; gossip concept not built.
- Hardening: formalize reward signals; add gossip channel; safeguards to prevent gaming (floors/ceilings, eval variance checks).

## Notes for future versions
- Formalize “lead the dance” in cards/orchestration.
- Add grounding/hallucination detector service.
- Build policy storage (tables/config) and licensing store.
- Implement Fireprompt/MDMAD services with safety rails.
- Add Tez ledger and bidding sandbox if pursued.
- Complete WS/SSE transport, memory service, research ingestion agents, Haze terrain API, and audit/simulation tools.
