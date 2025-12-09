# State of the Marketing Address – 2025-12-06

NorthStar “finished state” narrative for planning/Control Tower chats (non-coding). This describes what we will have once the backend capabilities are built and wired.

## Surfaces → Apps → Federations → Clusters → Agents
- Card-driven hierarchy where surfaces host apps; apps contain federations; federations orchestrate clusters of agents; clusters bundle tools/agents. Open-ended, additive via cards/manifest; any surface/app/cluster/agent can be added without code changes.
- Shared Nexus references per tenant/surface to align context.

## Tools
- Everything callable is a tool: agents, engines, connectors, external APIs. A unified tool registry (cards + backend) with Firearms metadata and scopes. Orchestrators only call registered tools.

## Rootsmanuva (routing)
- Deterministic routing engine that scores candidates (models, UI atoms, safety configs, etc.) using metric weights and fallbacks from card-defined profiles. Vendor/cloud agnostic; pluggable metrics from budget/eval/safety.

## Selecta Loop
- Periodic/triggered review loop (LLM-powered via selector_agent_card_id) proposes routing profile updates based on decision history and metric trends. Human/agent-approved changes update profiles; logged events for audit.

## Grounding & Hallucinations
- Standardized grounding layer: retrieval hooks, hallucination detectors, and 3-Wise checks; policies per surface to enforce grounding before responses/actions.

## Strategy Lock
- Mandatory HITL checkpoint after KPI/Budget/Firearms/3-Wise passes and before publish/execute. Logged and enforced in orchestration rails.

## Policies & Rules
- Hard rules in a policy store (tables/config, not Nexus). Nexus stays soft knowledge. Agents fetch policies; guardrails enforce them. Tenant-specific, auditable.

## 3-Wise LLM
- Card-driven fan-out to 3 distinct agents/models for risky decisions; no fixed prompts. Rootsmanuva can pick models; results logged with ModelCall/PromptSnapshot.

## Firearms Licenses
- License store gating destructive/risky actions. Tools/actions annotated with required licenses; guardrail adapter enforces. Agent identity supported via connectors.

## Floors & Ceilings (KPI/Budget corridors)
- Enforced KPI/Budget corridors: block/slow when ceilings hit; nudge when below floors. Orchestrator stages consult Budget/KPI services; logs decisions.

## KPI
- KPI corridors defined per tenant/surface/app; CRUD + enforcement in orchestrators; KPI deltas logged to Episodes; used for temperature and routing.

## Budgets
- Usage/billing ingestion (Vertex/Bedrock/CUR) into UsageMetric/CostRecord; BudgetService decisions feed Strategy Lock/Firearms/3-Wise; user-facing budget status.

## Autonomy
- Safe autonomy via combined policies/budgets/KPI/grounding/firearms/strategy lock. Sandbox/simulation modes to observe emergent behavior before production.

## Lead the Dance
- Agents/cluster manifests include “lead the dance” behaviors: proactively ask for missing context, propose next steps, and drive workflows while respecting safety rails. Logged clarify prompts; UX cues surfaced.

## Atoms Fam (targeted tokens)
- Scoped tokens per agent/tool for UI/content edits; per-token permissions; logs of token edits. Supports collaborative, narrow-scope agents without whole-document rewrites.

## Nexus (Haze)
- Vertex-backed Nexus with classifier and terrain aggregates. Haze 3D explorer surfaces Nexus docs (usage heatmap, tags, categories). Changes only via uploads/ingestion; no hard rules stored.

## Forecasting
- ForecastService wired to Vertex/BQ ML/AWS Forecast; forecasts stored and used for KPI/Budget planning and temperature loops; anomaly alerts.

## Tuning
- Eval pipelines (Vertex/Bedrock/Ragas) logging scores; integrated with routing metrics. Fireprompt-like prompt tuner available as a tool/HITL callable.

## Temperature
- Macro temperature per surface/app computed from KPIs/Budget/Eval; exposed to UI (e.g., header indicator) and routing/safety decisions.

## Meta-pidgen + Gossip
- PII-free gossip packets between agents; subscribe/publish model for sharing success signals; configurable per tenant.

## Blackboards
- Per-episode/per-conversation state (read/write) with retention; backed by Nexus/Firestore; accessible to agents and UI.

## Multi-tenant
- Strict tenant isolation in data and secrets; BYOK supported. Tenant_id flows through all models/logs; per-tenant tool/policy configs.

## Research → Nexus
- Research agents ingest external sources (papers, blogs, podcasts) into Nexus with classifiers/tags; PII/safety filters applied.

## Fireprompt
- Prompt optimization service/tool: runs evals/A/B tests, proposes prompt variants, HITL callable; logs deltas and improvements.

## MDMAD
- Long-plan execution assistant akin to Fireprompt: templates + safety checks + HITL; drives multi-step plans autonomously while respecting guardrails; leads the dance for long-running tasks.

## Orchestration
- Hybrid rails: deterministic stages + LLM agents. Runtimes for ADK/Bedrock/LangGraph with normalized traces into OrchestrationJob/Stage/AgentRun + ModelCall.

## Agent memory
- Memory service: episodic/conversation state stored/retrieved per agent; Nexus/blackboard-backed; configurable retention.

## Maybes
- Human scratchpad: MaybesNote model/service/APIs; EventLog on create/update/archive; optional Nexus mirroring later.

## Haze
- 3D vector explorer over Nexus with terrain API; Scene engine feeds scenes; FE renders walk-through of vector landscape; click-through to docs/episodes.

## Engines
- Proprietary engines (scene, audio/text/media, routing) with tests/logging/docs; callable as tools; replace third-party where needed.

## Emergence
- Safety rails + routing enable emergent behaviors while constrained by policies/budgets/KPI/grounding. Sandbox and audit to monitor emergence.

## Quantum
- Braket integration via connectors: QpuJobMetadata, logging (job_started/succeeded/failed), Firearms/HITL gating; datasets defined via cards; results logged to Nexus/EventLog.

## Cards (natural language control)
- All behaviors driven by cards/manifests (routing profiles, tools, prompts, 3-Wise, safety tunings). No fixed prompts in code; cards editable without deploys.

## Personalisation
- Cards carry persona/communication style per agent; work product rules separate from persona; manifests loaded per tenant/user/surface.

## Audit / Logs / Tuning / Debugging
- EventLog with PII strip; ModelCall/PromptSnapshot; routing decisions; budget hits; guardrail events; selection events; replay/simulation hooks; audit views for tuning and QA.

## Orchestration inspection
- Normalized traces from all runtimes; Agent Flow Viewer to inspect/change card-driven orchestration; simulate new setups safely.

## Chat / Realtime transport
- WebSockets for two-way control/chat; SSE for one-way status/“thinking”/canvas updates. Tokens streamed; statuses (thinking/planning/working) surfaced; multi-model routing underneath.

## Tez (internal currency)
- Optional internal ledger for agent bidding/swarms; sandboxed; safety rules for earning/spending; tenant-scoped.

## RL & RLHA
- Reward shaping via KPI/Budget/eval metrics; Strategy Lock as RLHA; gossip channel for reward signals; anti-gaming via floors/ceilings and eval variance checks.

## How to use this in Control Tower
- Treat this as the NorthStar end-state. Pair it with current “State of the World” to derive gaps/roadmaps.
- Use it to seed multi-LLM “state of the northstar address” (3-Wise style) to stress-test assumptions and plan implementations. 
