# ==============================================================================
# CANONICAL LOG FILE
#
# This is the single detailed log for this repo.
# The latest entry is always the latest understanding of that problem.
# Agents should read the log first before trying to solve something again.
# ==============================================================================
# LOG ENTRY FORMAT
#
# DATE/TIME: YYYY-MM-DD HH:MM:SS
# AGENT: Max | Gem | Claude | etc.
# PLAN_ID: The ID from the master plan file (e.g., PLAN-023)
# AREA: engines | infra | nexus | logging | etc.
# SUMMARY: One-line summary of the action or finding.
# DETAIL:
#   - What was tried.
#   - What failed.
#   - What worked.
# ARTEFACTS:
#   - Path to code/config/docs that were created/modified.
# ==============================================================================

# ENGINES · Implementation Log

Each entry:
- `YYYY-MM-DD · TaskID · PhaseID (if any) · Status · Short note · Commit/hash (if known)`

## Entries

- 2025-11-29 · E-00 · All · Done · Repo governance skeleton created for NorthStar Engines.
- 2025-11-30 · PLAN · Update · Added tracks C-01, G-01, P-01, T-01, N-01, S-01 to docs/20_SCENE_ENGINE_PLAN.md.
- 2025-11-30 · E-?? · Phase2 · In progress · Created skeleton directories/files for atomic engines (no logic yet).
- 2025-11-30 · SE-01.A · Done · Defined Scene Engine contracts and types (core/service schemas + validation tests).
- 2025-11-30 · SE-01.B · Done · Implemented FastAPI skeleton with /health and /scene/build endpoints (scene_engine service).
- 2025-11-30 · SE-01.C · Done · Built grid/box normaliser with validation tests.
- 2025-11-30 · SE-01.D · Done · Added grid→world mapping and wall/vector_explorer recipes; wired into service pipeline.
- 2025-11-30 · SE-01.F · Done · Added Dockerfile, README, and run_local script for Scene Engine.
- 2025-11-30 · SE-01.G · Done · Added Cloud Run stub manifest and deployment notes for Scene Engine.
- 2025-11-30 · C-01.A · Done · Defined Chat Surface contracts and schemas with validation tests.
- 2025-11-30 · C-01.B · Done · Implemented Chat service skeleton with health and POST routes plus tests.
- 2025-11-30 · C-01.C · Done · Stubbed chat actions endpoints and schemas with basic tests.
- 2025-11-30 · G-01.A · Done · Added Strategy Lock schemas and stub engine with tests.
- 2025-11-30 · G-01.B · Done · Added 3-Wise LLM schemas and stub engine with tests.
- 2025-11-30 · P-01.A · Done · Implemented PII strip schemas and stub engine with tests.
- 2025-11-30 · P-01.B · Done · Added DataPolicyDecision schema within PII engine.
- 2025-11-30 · T-01.A · Done · Added control state schemas and tests for mechanical naming and corridors.
- 2025-11-30 · T-01.B · Done · Added stub temperature engine returning TemperatureState with tests.
- 2025-11-30 · N-01.A · Done · Added Nexus schemas and tests for space naming and queries.
- 2025-11-30 · N-01.B · Done · Added DatasetEvent canonical schema and tests.
- 2025-11-30 · S-01.A · Done · Added stub logging engine accepting DatasetEvent with tests.
- 2025-11-30 · E-02.A · Done · Defined IO contracts for AUDIO.SEGMENT.FFMPEG_V1 (types.py).
- 2025-11-30 · E-02.B · Done · Implemented ffmpeg segmentation engine logic for AUDIO.SEGMENT.FFMPEG_V1.
- 2025-11-30 · E-02.C · Done · Added unit tests for AUDIO.SEGMENT.FFMPEG_V1.
- 2025-11-30 · E-02.A · Done · Defined IO contracts for AUDIO.INGEST.LOCAL_FILE_V1 (types.py).
- 2025-11-30 · E-02.B · Done · Implemented file staging for AUDIO.INGEST.LOCAL_FILE_V1.
- 2025-11-30 · E-02.C · Done · Added unit test for AUDIO.INGEST.LOCAL_FILE_V1.
- 2025-11-30 · E-02.A · Done · Defined IO contracts for AUDIO.INGEST.REMOTE_PULL_V1 (types.py).
- 2025-11-30 · E-02.B · Done · Implemented remote pull ingest (urllib) for AUDIO.INGEST.REMOTE_PULL_V1.
- 2025-11-30 · E-02.C · Done · Added unit tests for AUDIO.INGEST.REMOTE_PULL_V1.
- 2025-11-30 · E-02.A · Done · Defined IO contracts for AUDIO.INGEST.LOCAL_V1 (types.py).
- 2025-11-30 · E-02.B · Done · Implemented local dir ingest (recursive copy) for AUDIO.INGEST.LOCAL_V1.
- 2025-11-30 · E-02.C · Done · Added unit test for AUDIO.INGEST.LOCAL_V1.
- 2025-11-30 · E-02.A · Done · Defined IO contracts for AUDIO.PREPROCESS.BASIC_CLEAN_V1, AUDIO.ASR.WHISPER_V1, TEXT.NORMALISE.SLANG_V1, TEXT.CLEAN.ASR_PUNCT_CASE_V1, AUDIO.BEAT.FEATURES_V1, ALIGN.AUDIO_TEXT.BARS_V1, TAG.FLOW.AUTO_V1, DATASET.PACK.JSONL_V1, VIDEO.INGEST.FRAME_GRAB_V1, TRAIN.LORA.LOCAL_V1, TRAIN.LORA.PEFT_HF_V1 (types.py files).
- 2025-11-30 · E-02.B · Done · Implemented minimal run logic for engines above (copy/normalize stubs, ASR stub, slang normalization, beat metadata stub, alignment, flow tagging, JSONL packing, frame grab placeholder, LoRA stubs).
- 2025-11-30 · E-02.C · Done · Added unit tests for all engines above.
- 2025-11-30 · E-02.B · Update · Hardened preprocessing (ffmpeg loudnorm/filters) and flow tagging heuristics; updated tests.
- 2025-11-30 · E-02.B · Update · Frame grabber now uses ffmpeg (auto/manual); beat_features uses librosa; added tests and requirement update.
- 2025-11-30 · E-02.B · Update · Added audio_core layer (ASR fallback, dataset builder, LoRA stub trainer, pipeline runner); BBK manifest/runner wired to audio_core.
- 2025-11-30 · E-02.B · Update · Added torch/faster-whisper deps; upgraded LoRA trainer (torch tiny loop fallback/unavailable path), ASR backend retains graceful fallback.
- 2025-11-30 · BBK · Service · Added local FastAPI wrapper for upload/process and start-training; tests and README.
- 2025-11-30 · ENGINE-001.E · DONE · Registered scene engines and combos in registry; marked ENGINE-001 done.
- 2025-11-30 · ENGINE-002.D · DONE · Added CLI runner for AUDIO.INGEST.LOCAL_V1.
- 2025-11-30 · ENGINE-003.D · DONE · Added CLI runner for AUDIO.INGEST.LOCAL_FILE_V1.
- 2025-11-30 · ENGINE-004.D · DONE · Added CLI runner for AUDIO.INGEST.REMOTE_PULL_V1.
- 2025-11-30 · ENGINE-005.D · DONE · Added CLI runner for AUDIO.PREPROCESS.BASIC_CLEAN_V1.
- 2025-11-30 · ENGINE-006.D · DONE · Added CLI runner for AUDIO.SEGMENT.FFMPEG_V1.
- 2025-11-30 · ENGINE-007.D · DONE · Added CLI runner for AUDIO.ASR.WHISPER_V1.
- 2025-11-30 · ENGINE-008.D · DONE · Added CLI runner for TEXT.NORMALISE.SLANG_V1.
- 2025-11-30 · ENGINE-009.D · DONE · Added CLI runner for TEXT.CLEAN.ASR_PUNCT_CASE_V1.
- 2025-11-30 · ENGINE-010.D · DONE · Added CLI runner for AUDIO.BEAT.FEATURES_V1.
- 2025-11-30 · ENGINE-011.D · DONE · Added CLI runner for ALIGN.AUDIO_TEXT.BARS_V1.
- 2025-11-30 · ENGINE-012.D · DONE · Added CLI runner for TAG.FLOW.AUTO_V1.
- 2025-11-30 · ENGINE-013.D · DONE · Added CLI runner for DATASET.PACK.JSONL_V1.
- 2025-11-30 · ENGINE-014.D · DONE · Added CLI runner for TRAIN.LORA.LOCAL_V1.
- 2025-11-30 · ENGINE-015.D · DONE · Added CLI runner for TRAIN.LORA.PEFT_HF_V1.
- 2025-11-30 · ENGINE-016.D · DONE · Added CLI runner for VIDEO.INGEST.FRAME_GRAB_V1.
- 2025-11-30 · ENGINE-001 · DONE · All phases complete; scene engine marked done in plan.- 2025-12-01 · AGENT: Max · PLAN_ID: PLAN-023 · AREA: Phase0 · SUMMARY: Contracts and required engines documented · DETAIL: Added PLAN-023 contracts doc with shapes, engine vs agent rule, required engines, behaviour boundaries; added OS v0 status map file marking required/not required engines. · ARTEFACTS: docs/plan/PLAN-023.md; engines/registry/os_v0_status.json
- 2025-12-01 · AGENT: Max · PLAN_ID: PLAN-023 · AREA: Phase1 · SUMMARY: Infra/secrets requirements captured (repo-only) · DETAIL: Documented GCP/AWS endpoints, buckets, DB, IAM, and secret/env naming; provisioning remains external. · ARTEFACTS: docs/infra/PLAN-023_INFRA.md
- 2025-12-01 · AGENT: Max · PLAN_ID: PLAN-023 · AREA: Phase2 · SUMMARY: Core brain wiring spec (repo-only) · DETAIL: Captured chat/Nexus/Temperature/Guardrails/PII/logging wiring guidance with env-driven endpoints; behaviour remains in agents. · ARTEFACTS: docs/infra/PLAN-023_PIPELINE.md
- 2025-12-01 · AGENT: Max · PLAN_ID: PLAN-023 · AREA: Phase3 · SUMMARY: Placeholder app/federation cards defined · DETAIL: Added placeholder app and federation cards referencing surfaces, agents, and Nexus spaces to prove wiring without app semantics. · ARTEFACTS: docs/cards/plan-023/placeholder_app.json; docs/cards/plan-023/placeholder_federation.json
- 2025-12-01 · AGENT: Max · PLAN_ID: PLAN-023 · AREA: Phase4 · SUMMARY: Hardening/extension guidance captured · DETAIL: Documented logging/metrics/autoscaling/retries plus extension rules; restates no app behaviour in engines without cards. · ARTEFACTS: docs/infra/PLAN-023_HARDENING.md
- 2025-12-01 · AGENT: Max · PLAN_ID: PLAN-024 · AREA: Phase0 · SUMMARY: Contracts defined and transports stubbed · DETAIL: Added Thread/Message/Contact schemas and in-memory pub/sub with HTTP/WS/SSE transports plus aggregate server and README; tests cover contracts and transports. · ARTEFACTS: engines/chat/contracts.py; engines/chat/service/{transport_layer.py,http_transport.py,ws_transport.py,sse_transport.py,server.py}; engines/chat/tests/*.py; engines/chat/README.md
- 2025-12-02 · AGENT: Max · PLAN_ID: PLAN-026 · AREA: prod-wiring · SUMMARY: Wired chat pipeline to LLM client hook, added media ingest endpoints, Cloud Run manifest, and dev runtime doc. · DETAIL: Added Vertex-compatible `llm_client` with streaming path in chat pipeline, HTTP/WS/SSE share it; media upload/stack endpoints write to GCS via helper and Nexus/logging; added env_dev settings helper and dev runtime doc plus Cloud Run manifest/script. · ARTEFACTS: engines/chat/service/llm_client.py, engines/chat/pipeline.py, engines/media/service/routes.py, engines/media/tests/test_media_endpoints.py, engines/config/env_dev.py, docs/infra/ENGINES_DEV_RUNTIME.md, deploy/dev/engines-chat.yaml, deploy/dev/deploy_chat.sh

DATE/TIME: 2025-12-02 18:00:00
AGENT: Gil
PLAN_ID: UNPLANNED
AREA: caidence-prod-wiring
SUMMARY: Wired Nexus/Storage adapters, chat pipeline, guardrails, temperature, and SEO primitives.
DETAIL:
  - Added runtime config, Firestore Nexus backend + factory, and GCS storage helper; ingest engines upload to GCS when buckets set.
  - Chat HTTP/WS/SSE routes now use a pipeline that logs to Nexus/logging and returns orchestration stubs instead of echo.
  - Implemented regex PII strip, policy-aware guardrails (strategy lock/3-wise), weighted temperature engine, and logging with PII enforcement.
  - Extended DatasetEvent with SEO/analytics fields; added SEO/FUME primitives doc and wiring notes for CAIDENCE.
ARTEFACTS:
  - engines/config/runtime_config.py
  - engines/nexus/backends/*
  - engines/storage/gcs_client.py
  - engines/chat/pipeline.py and transport updates
  - engines/guardrails/*, engines/control/temperature/engine.py
  - engines/dataset/events/schemas.py
  - docs/infra/ENGINES_WIRING_CAIDENCE.md, docs/constitution/SEO_FUME_PRIMITIVES.md

DATE/TIME: 2025-12-01 12:00:00
AGENT: Gil
PLAN_ID: PLAN-025
AREA: infra
SUMMARY: Dev infra baseline locked and anti-drift rule added.
DETAIL:
  - Created the canonical dev infra doc and added Article 6 to the constitution to prevent infra drift without a plan.
ARTEFACTS:
  - docs/constitution/INFRA_GCP_DEV.md
  - docs/00_CONSTITUTION.md

DATE/TIME: 2025-12-01 12:00:00
AGENT: Gil
PLAN_ID: PLAN-026
AREA: infra/contracts
SUMMARY: Reset Max onto dev infra baseline, locked anti-drift rules.
DETAIL:
  - Pointed Max at INFRA_GCP_DEV.md, enforced single-plan-file rule, and authorised real chat/Nexus/Vertex wiring under PLAN-026 only.
ARTEFACTS:
  - docs/02_REPO_PLAN.md
  - docs/constitution/INFRA_GCP_DEV.md

- 2025-12-02 · AGENT: Gil · PLAN_ID: PLAN-RECON · AREA: repo-recon · SUMMARY: Quick repo recon run · DETAIL: Produced docs/run_reports/max_recon_summary.json and docs/run_reports/max_recon_human.txt. See files for counts, sample paths and immediate action items. · ARTEFACTS: docs/run_reports/max_recon_summary.json, docs/run_reports/max_recon_human.txt
- 2025-12-02 · AGENT: Max · PLAN_ID: PLAN-CANONICAL · AREA: governance · SUMMARY: Consolidated planning to single canonical file docs/02_REPO_PLAN.md; marked legacy plan docs read-only. · ARTEFACTS: docs/02_REPO_PLAN.md, docs/plan/PLAN-023.md, docs/plan/PLAN-024.md, docs/infra/PLAN-023_INFRA.md, docs/infra/PLAN-023_PIPELINE.md, docs/infra/PLAN-023_HARDENING.md
- 2025-12-03 · AGENT: Max · PLAN_ID: PLAN-0AI · AREA: vector-explorer · SUMMARY: Implemented vector explorer backend (phases 0-4) with Firestore corpus contract, vector query/mapping engine, HTTP scene route, logging, and docs. · ARTEFACTS: docs/infra/VECTOR_CORPUS_CONTRACT.md, docs/infra/VECTOR_EXPLORER_SCENE_MAPPING.md, docs/infra/VECTOR_EXPLORER_HOWTO.md, engines/nexus/vector_explorer/*, engines/scene_engine/core/types.py, engines/scene_engine/core/mapping.py, engines/chat/service/server.py, tests under engines/nexus/vector_explorer/tests.
- 2025-12-03 · AGENT: Max · PLAN_ID: PLAN-0AL · AREA: haze-vector-ingest · SUMMARY: Delivered production ingest + 3D explorer path using real embeddings/vector store and corpus; added ingest endpoint, logging, and tests. · ARTEFACTS: engines/nexus/vector_explorer/ingest_service.py, engines/nexus/vector_explorer/vector_store.py, engines/nexus/vector_explorer/ingest_routes.py, engines/nexus/vector_explorer/routes.py, engines/nexus/vector_explorer/tests/*, docs/02_REPO_PLAN.md, docs/infra/VECTOR_EXPLORER_*.
- 2025-12-03 · AGENT: Max · PLAN_ID: LOCAL-RUN · AREA: dev-runtime · SUMMARY: Standardised local dev run flow with .venv and uvicorn chat server exposing vector explorer; added quickstart doc. · ARTEFACTS: docs/infra/ENGINES_DEV_RUN_LOCAL.md.
- 2025-12-03 · AGENT: Max · PLAN_ID: OPS_HELPER · AREA: vector-config · SUMMARY: Added Vertex index/endpoint create commands and dev model defaults (text-embedding-004, multimodalembedding@001) to local/dev run guides; placeholders for INDEX_ID/ENDPOINT_ID kept for ops fill-in. · ARTEFACTS: docs/infra/VECTOR_EXPLORER_DEV_RUN.md, docs/infra/ENGINES_DEV_RUN_LOCAL.md.
- 2025-12-06 · AGENT: Max · PLAN_ID: PLAN-CANONICAL-REFRESH · AREA: governance/infra · SUMMARY: Merged legacy plan docs into docs/02_REPO_PLAN.md, removed old plan files, and documented agent touchpoints + current sitemap. · DETAIL: Added Historical Plans section and consolidation log; created docs/infra/ENGINES_AGENT_TOUCHPOINTS.md (LLM/agent recon) and docs/infra/ENGINES_SITEMAP_CURRENT.md; deleted legacy plan files per single-plan rule. · ARTEFACTS: docs/02_REPO_PLAN.md, docs/infra/ENGINES_AGENT_TOUCHPOINTS.md, docs/infra/ENGINES_SITEMAP_CURRENT.md.
- 2025-12-21 · AGENT: Codex · PLAN_ID: PLAN-READINESS-UNBLOCK · AREA: readiness · SUMMARY: Added Engines readiness unblock plan with lane-specific TODOs and VTE gates. · COMMIT: 4f1531fea37eb06a5eace0cd777d53c66df0448c · ARTEFACTS: docs/infra/ENGINES_READINESS_UNBLOCK_PLAN.md.
