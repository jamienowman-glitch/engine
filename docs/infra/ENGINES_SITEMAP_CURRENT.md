# ENGINES_SITEMAP_CURRENT

Current repo structure (high level).

## Top-level
- `apps/` – sample or auxiliary apps (e.g., bbk-local-ui).
- `bossman/` – BOSSMAN rituals and state-of-the-world/marketing address docs.
- `deploy/` – deployment manifests/scripts (e.g., Cloud Run for chat/media).
- `docs/` – constitution, infra, plans, logs, cards.
- `engines/` – all backend engines/services.
- `sample_media/` – media samples for tests/demos.
- `tests/` – repo-level tests (if any).
- `requirements.txt` – Python deps.

## Key engine subdirectories
- `engines/chat/` – chat pipeline, HTTP routes, Vertex LLM client, logging to Nexus.
- `engines/media/` – media upload/list endpoints with Nexus/logging.
- `engines/nexus/` – Nexus schemas, Firestore backend, vector store (Vertex), RAG service.
- `engines/logging/` – logging engine with PII stripping, Nexus persistence.
- `engines/scene_engine/` – 3D scene builder service (FastAPI) + recipes.
- `engines/orchestration/` – agent runtime adapter interfaces (ADK/Bedrock/LangGraph) and mapping utilities.
- `engines/rootsmanuva_engine/` – deterministic routing (Rootsmanuva) and Selecta Loop interface.
- `engines/budget/`, `engines/forecast/`, `engines/eval/`, `engines/security/`, `engines/creative/`, `engines/safety/` – cost/forecast/eval/security/creative/QPU/safety services and schemas.
- `engines/control/`, `engines/dataset/`, `engines/guardrails/`, `engines/reactive/`, `engines/seo/`, `engines/storage/`, `engines/text/`, `engines/audio/`, etc. – various domain engines (temperature/KPI, dataset events, guardrails, reactive content, SEO, storage helpers, text/audio processors).

## Docs highlights
- `docs/constitution/` – core contracts (manifest/token graph, capabilities, tool registry, FIREARMS_AND_HITL, etc.).
- `docs/infra/` – infra notes, runtime config, agent touchpoints, current sitemap (this doc).
- `docs/logs/` – engine change logs.
- `docs/cards/` – card examples (e.g., placeholder app/federation).
- `docs/02_REPO_PLAN.md` – single canonical plans file.

## Related target / vision docs
- docs/constitution/ORCHESTRATION_PATTERNS.md – Orchestration target patterns (rails + agent/tool calls).
- docs/constitution/MANIFEST_TOKEN_GRAPH.md – Canonical manifest/token graph contract.
- docs/constitution/CLUSTER_CAPABILITIES.md – Target capability scoping for clusters/agents.
- docs/constitution/DESIGN_TOOLS_SCOPING.md – Target manifest/capability model for creative tools.
- docs/infra/TILES_WIRING.md – Target wiring for tiles/logging/capabilities.
- docs/caidence2/engine_mapping.md – Mapping to ADK manifests/routes (target alignment).

Primary target sitemap candidate: docs/constitution/ORCHESTRATION_PATTERNS.md (captures desired orchestration layout and interactions).
