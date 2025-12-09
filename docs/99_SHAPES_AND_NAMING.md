# SHAPES AND NAMING REFERENCE

Canonical shapes/naming gathered from repo planning/impl. Planning-only; do not rename without audit. Marked inconsistencies as INCONSISTENT_* and planned-only secrets as PLANNED_SECRET_*.

## Tenants
- Pattern: `t_<slug>` (e.g., `t_northstar-dev`, `t_snakeboard-uk`).
- Fields (planning): tenant_id, display_name, plan_tier, billing_mode, created_at, updated_at (per TENANTS_AUTH_BYOK).

## Secrets / connectors
- Connectors: `conn.<provider>.<product>.<scope>`.
- GSM secrets:
  - OS-paid: `conn-<provider>-<product>-<scope>-key`.
  - BYOK: `tenant-<tenant_id>-<provider>-<product>-<scope>-key`.
- Eval: VERTEX_EVAL_MODEL_ID, BEDROCK_EVAL_MODEL_ID, RAGAS_EVAL_URL, RAGAS_EVAL_TOKEN.
- Vector/RAG: VECTOR_INDEX_ID, VECTOR_ENDPOINT_ID, VECTOR_PROJECT_ID, TEXT_EMBED_MODEL, IMAGE_EMBED_MODEL.
- Forecast: VERTEX_FORECAST_DATASET/TABLE, BQ_ML_FORECAST_DATASET/TABLE, AWS_FORECAST_ROLE_ARN, AWS_FORECAST_DATASET_GROUP.
- Billing/usage (env getters): GHAS_APP_ID, GHAS_PRIVATE_KEY_SECRET, DEPENDABOT_TOKEN_SECRET, SEMGREP_TOKEN_SECRET, SONAR_TOKEN_SECRET, IMAGEN_API_KEY_SECRET, NOVA_API_KEY_SECRET, BRAKET_ROLE_ARN, BRAKET_REGION. (Connector secret names for Bedrock/Vertex billing/Braket role may still be missing—mark MISSING_CANONICAL_SECRET_* as needed.)

## Core models (engines/planning)
- NexusDocument: id, text, tenant_id, env, kind, tags[], metadata{}, refs{}, category/bin (string), tenant_local_space (optional).
- NexusEmbedding: doc_id, tenant_id, env, kind, embedding[], model_id, dimensions?, metadata{}, timestamps.
- NexusUsage: tenant_id, env, doc_ids[], purpose, agent_id?, episode_id?, scores?, created_at?.
- NexusUsageAggregate (planned): doc_id, tenant_id, total_hits, last_used_at, distinct_agents, distinct_episodes, height_score?, coords? (terrain API).
- DatasetEvent: tenantId, env, surface, agentId, input{}, output{}, pii_flags{}, train_ok, metadata{}, UTM/SEO fields.
- ModelCallLog/PromptSnapshot (planning/engines/nexus/logging.py): call_id, tenant_id, env, model_id, purpose, prompt{text, created_at}, output_dimensions, episode_id?.
- EvalJob: job_id, tenant_id, episode_id?, eval_kind, backend, status, scores{}, raw_payload{}, model_call_ids[], prompt_snapshot_refs[], created_at, updated_at.
- UsageMetric: tenant_id, vendor, model, surface?, app?, agent_id?, tokens?, calls?, cost_estimate?, timeframe, metadata{}, created_at.
- CostRecord: tenant_id, vendor, service, cost, period, source_ref?, created_at.
- ForecastSeries: series_id, metric_type, tenant_id, scope, cadence, history_ref, metadata{}.
- ForecastJob: job_id, backend, status, horizon, series_id, confidence_intervals{}, results_ref?, created_at, updated_at.
- SecurityFinding: id, tenant_id, source, severity, location, description, cwe?, status, created_at.
- SecurityScanRun: run_id, source, repo_ref, started_at, completed_at?, findings_ref?, status.
- CreativeEval: id, tenant_id, artefact_ref, backend, scores{}, eval_payload_ref?, created_at.
- QpuJobMetadata: job_id, backend, tenant_id, episode_id?, parameters_ref?, results_ref?, status, device?, shots?, region?, s3_bucket?, s3_prefix?, created_at, completed_at?.
- SafetyContext: tenant_id, actor?, licences[], kpi_snapshot{}, budget_snapshot{}, tools[], nexus_refs{}, agent_id?, episode_id?, metadata{}.
- GuardrailVerdict: vendor_verdict?, firearms_verdict?, three_wise_verdict?, result, reasons[], tenant_id?, agent_id?, episode_id?, created_at.
- Agent runtime (planning): AgentStepRequest/Result, WorkflowRequest/Result (ids, input/context/traces/model_calls).
- Orchestration/Logging (planning): OrchestrationJob/Stage/AgentRun, ModelCall, PromptSnapshot, TokenEvent/TokenContext/TokenCandidates/TokenEdits/TokenOutcome, Episode, EventLog header – shapes not fully defined in this repo; treat existing names as canonical and mark INCONSISTENT_* if diverging elsewhere.
- MaybesNote (planning): maybes_id, tenant_id, user_id, title?, body, colour_token, layout_x, layout_y, layout_scale, tags[], origin_ref, is_pinned, is_archived, created_at, updated_at, episode_id?, nexus_doc_id?; asset_type="maybes_note".

## Notes on hard rules vs Nexus
- Hard rules (Firearms/HITL/Strategy Lock) live in docs/constitution; no Nexus storage planned. If found in Nexus elsewhere, mark INCONSISTENT_RULE_STORAGE and plan migration to tables/config.
