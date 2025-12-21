# ==============================================================================
# REPO MASTER PLAN
#
# This is the single canonical plans file for this repo.
# All older scattered plan docs are now considered read-only history.
# Future plans must be appended here only.
# ==============================================================================

# HOW TO USE THIS FILE
#
# Every new plan entry gets:
# - a unique sequential ID (e.g., PLAN-023, PLAN-024), continuing from the highest ID.
# - a status field: PENDING, ACTIVE, or DONE.
# - space for each agent to write their notes / results.
#
# Planning agents (e.g., Gem):
# - Create new entries as PENDING.
# - Leave a clear "Implementation Notes for Max" subsection.
# - Specify which engines/areas the plan touches.
#
# Implementer agents (e.g., Max):
# - Change status from PENDING -> ACTIVE when starting work.
# - Change status from ACTIVE -> DONE when finished.
# - Add any technical notes/decisions to the log file.
#
# Reviewer/safety agents (e.g., Claude):
# - Add review notes under a separate "Review Notes" subheading.
# - Do not create new plan IDs, only annotate existing ones.

---
NOTE (System): This is the ONLY planning document for this repo. All agents and humans MUST add/modify tasks here. No other plan files are allowed.

# REPO MASTER PLAN

Status: DONE
Owner: Control Tower (Jay)
Last updated: 2025-11-30

---

## A. Global Overview

This repository contains **engines** for the NorthStar OS. Engines are headless, reusable components that take structured input and produce structured output. They are designed to be driven by other systems, such as UIs, batch jobs, or other agents.

All work in this repo is governed by two key documents:
-   **`docs/00_CONSTITUTION.md`**: The "why" and "how we behave." Defines roles, principles, and safety rules.
-   **`docs/01_FACTORY_RULES.md`**: The "how we build." Defines processes for planning, logging, testing, and file structures.

All tasks are defined below as `ENGINE-XXX` blocks.

---

## B. Engine Tasks

### ENGINE-001 – Core Scene Engine v1

Legacy ID: SE-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement a Scene Engine as an HTTP service that accepts a description of a grid and a list of items (`boxes`) and returns a standard 3D Scene JSON object. It supports layout "recipes" to arrange content, starting with a flat "wall" and a 3D "vector_explorer".

**Files to touch**
- `engines/scene-engine/` (and subdirectories for service, core, recipes, tests)
- `engines/scene-engine/Dockerfile`
- `engines/registry/engine_registry.json`
- `docs/logs/ENGINES_LOG.md`

**Phases**
- Phase A – Contracts & Types (✅ DONE)
- Phase B – HTTP Service Skeleton (✅ DONE)
- Phase C – Grid & Box Normalisation Engine (✅ DONE)
- Phase D – Grid→World Mapping & Recipes (✅ DONE)
- Phase E – Engines Registry Hooks (✅ DONE)
- Phase F – Docker & Local Container (✅ DONE)
- Phase G – Minimal Deployment Lane (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you start this engine, set `Status: ACTIVE`.
  - When you finish all phases, set `Status: DONE` and add a one-line completion note with date.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note under this block.

Completed: 2025-11-30 – Registry entries and combos added for Scene Engine components.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-002 – Atomic Engine: audio/ingest_local

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/ingest_local` atomic engine, which syncs a local directory or GCS inbox to the local working directories.

**Files to touch**
- `engines/audio/ingest_local/types.py`
- `engines/audio/ingest_local/engine.py`
- `engines/audio/ingest_local/tests/test_ingest_local.py`
- `engines/audio/ingest_local/runner.py`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you start this engine, set `Status: ACTIVE`.
  - When you finish all phases, set `Status: DONE` and add a one-line completion note with date.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note under this block.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-003 – Atomic Engine: audio/ingest_local_file

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/ingest_local_file` atomic engine, which stages local audio/video files into a working inbox.

**Files to touch**
- `engines/audio/ingest_local_file/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-004 – Atomic Engine: audio/ingest_remote_pull

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/ingest_remote_pull` atomic engine, which pulls remote audio/video to local staging.

**Files to touch**
- `engines/audio/ingest_remote_pull/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-005 – Atomic Engine: audio/preprocess_basic_clean

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/preprocess_basic_clean` atomic engine for basic noise/level cleanup.

**Files to touch**
- `engines/audio/preprocess_basic_clean/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-006 – Atomic Engine: audio/segment_ffmpeg

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/segment_ffmpeg` atomic engine to segment audio using FFmpeg.

**Files to touch**
- `engines/audio/segment_ffmpeg/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-007 – Atomic Engine: audio/asr_whisper

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/asr_whisper` atomic engine as a wrapper for Whisper ASR.

**Files to touch**
- `engines/audio/asr_whisper/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-008 – Atomic Engine: text/normalise_slang

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `text/normalise_slang` atomic engine for slang-preserving text normalization.

**Files to touch**
- `engines/text/normalise_slang/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-009 – Atomic Engine: text/clean_asr_punct_case

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `text/clean_asr_punct_case` atomic engine to restore punctuation and casing.

**Files to touch**
- `engines/text/clean_asr_punct_case/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-010 – Atomic Engine: audio/beat_features

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `audio/beat_features` atomic engine to analyze beat and tempo.

**Files to touch**
- `engines/audio/beat_features/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-011 – Atomic Engine: align/audio_text_bars

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `align/audio_text_bars` atomic engine to align words to musical bars.

**Files to touch**
- `engines/align/audio_text_bars/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-012 – Atomic Engine: tag/flow_auto

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `tag/flow_auto` atomic engine for rule-based flow tagging.

**Files to touch**
- `engines/tag/flow_auto/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-013 – Atomic Engine: dataset/pack_jsonl

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `dataset/pack_jsonl` atomic engine to package data into JSONL format.

**Files to touch**
- `engines/dataset/pack_jsonl/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-014 – Atomic Engine: train/lora_local

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `train/lora_local` atomic engine as a placeholder for local LoRA training.

**Files to touch**
- `engines/train/lora_local/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-015 – Atomic Engine: train/lora_peft_hf

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `train/lora_peft_hf` atomic engine for LoRA fine-tuning via PEFT/HuggingFace.

**Files to touch**
- `engines/train/lora_peft_hf/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-016 – Atomic Engine: video/frame_grab

Legacy ID: E-02
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Implement the `video/frame_grab` atomic engine to grab representative frames from video uploads.

**Files to touch**
- `engines/video/frame_grab/`

**Phases**
- Phase A – Contracts & IO Types (✅ DONE)
- Phase B – Minimal Implementation (✅ DONE)
- Phase C – Unit Tests (✅ DONE)
- Phase D – Simple Runner (Optional) (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Added CLI runner; all phases complete.
QA: PASS (2025-11-30) - Verified all phases are complete as marked.

---

### ENGINE-017 – Chat Surface & Core Contracts

Legacy ID: C-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Define the HTTP contracts and data shapes used by the shared Chat Surface across all apps. This creates the thin Python service layer that receives chat requests, calls internal engines, and streams back responses, without any specific backend (e.g., ADK) wiring.

**Files to touch**
- `engines/chat/service/`
- `engines/chat/tests/`

**Phases**
- Phase A – Chat Contracts & Schemas (✅ DONE)
- Phase B – Chat Service Skeleton (✅ DONE)
- Phase C – Message Actions Contracts (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – All phases for defining chat contracts and service stubs are complete.
QA: PASS (2025-11-30) - Schemas, routes, and stubs are implemented as per the plan.

---

### ENGINE-018 – Guardrails: Strategy Lock & 3-Wise LLM

Legacy ID: G-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Define the core guardrail engines that sit behind the chat actions: the Strategy Lock planner and the 3-Wise LLM risk panel. These are pure, internal engines with no external API calls.

**Files to touch**
- `engines/guardrails/strategy_lock/`
- `engines/guardrails/three_wise/`

**Phases**
- Phase A – Strategy Lock Engine Plan (✅ DONE)
- Phase B – 3-Wise LLM Engine Plan (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Contracts and stub engines for Strategy Lock and 3-Wise LLM are complete.
QA: PASS (2025-11-30) - Schemas and stub `run()` functions are implemented as planned.

---

### ENGINE-019 – PII & Data Hygiene

Legacy ID: P-01
Status: DONE
Planner Gil
Implementer: Max
QA: Claude

**Goal**
Define reusable engines for stripping PII from text and creating `DataPolicyDecision` attachments to flag data safety for training purposes.

**Files to touch**
- `engines/guardrails/pii_text/`

**Phases**
- Phase A – Text PII Strip Engine (✅ DONE)
- Phase B – PII Policy Attachments (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – PII stripping engine contracts and policy schemas are complete.
QA: PASS (2025-11-30) - All specified schemas and stub engines are implemented.

---

### ENGINE-020 – Temperature, KPIs & Budgets

Legacy ID: T-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Provide a single control brain for Temperature bands, KPI corridors, and budget ceilings/floors by defining the core state schemas and a stub Temperature engine.

**Files to touch**
- `engines/control/state/`
- `engines/control/temperature/`

**Phases**
- Phase A – State Schemas & Mechanical Names (✅ DONE)
- Phase B – Temperature Engine Plan (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Control plane state schemas and Temperature engine contracts are complete.
QA: PASS (2025-11-30) - All specified schemas and stub engines are implemented.

---

### ENGINE-021 – Nexus & Datasets

Legacy ID: N-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Define how engines interact with Nexus (data/research/style) and how training examples are logged in a PII-safe way by defining the core schemas for spaces and events.

**Files to touch**
- `engines/nexus/`
- `engines/dataset/events/`

**Phases**
- Phase A – Nexus Spaces & IDs (✅ DONE)
- Phase B – Dataset Event Schema (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – Nexus and Dataset event schemas are defined and implemented.
QA: PASS (2025-11-30) - All specified schemas are implemented and tested.

---

### ENGINE-022 – SEOUTM & Event Logging

Legacy ID: S-01
Status: DONE
Planner: Gil
Implementer: Max
QA: Claude

**Goal**
Ensure all logging is built with SEO/UTM-awareness from Day One by defining a central logging engine that consumes the canonical `DatasetEvent`.

**Files to touch**
- `engines/logging/events/`

**Phases**
- Phase A – Logging Engine Plan (✅ DONE)

**Ritual**
- For Max (Implementer):
  - When you finish all phases, set `Status: DONE` and add a one-line completion note.
- For Claude (QA):
  - After Max marks DONE, add a `QA: PASS` or `QA: FAIL` note.

Completed: 2025-11-30 – The central logging engine contract is defined and stubbed.
QA: PASS (2025-11-30) - Stub engine and tests are implemented as planned.

---

## C. Completed Engines

| Engine ID | Name | Status | QA |
|---|---|---|---|
| ENGINE-001 | Core Scene Engine v1 | DONE | PASS |
| ENGINE-002 | Atomic Engine: audio/ingest_local | DONE | PASS |
| ENGINE-003 | Atomic Engine: audio/ingest_local_file | DONE | PASS |
| ENGINE-004 | Atomic Engine: audio/ingest_remote_pull | DONE | PASS |
| ENGINE-005 | Atomic Engine: audio/preprocess_basic_clean | DONE | PASS |
| ENGINE-006 | Atomic Engine: audio/segment_ffmpeg | DONE | PASS |
| ENGINE-007 | Atomic Engine: audio/asr_whisper | DONE | PASS |
| ENGINE-008 | Atomic Engine: text/normalise_slang | DONE | PASS |
| ENGINE-009 | Atomic Engine: text/clean_asr_punct_case | DONE | PASS |
| ENGINE-010 | Atomic Engine: audio/beat_features | DONE | PASS |
| ENGINE-011 | Atomic Engine: align/audio_text_bars | DONE | PASS |
| ENGINE-012 | Atomic Engine: tag/flow_auto | DONE | PASS |
| ENGINE-013 | Atomic Engine: dataset/pack_jsonl | DONE | PASS |
| ENGINE-014 | Atomic Engine: train/lora_local | DONE | PASS |
| ENGINE-015 | Atomic Engine: train/lora_peft_hf | DONE | PASS |
| ENGINE-016 | Atomic Engine: video/frame_grab | DONE | PASS |
| ENGINE-017 | Chat Surface & Core Contracts | DONE | PASS |
| ENGINE-018 | Guardrails: Strategy Lock & 3-Wise LLM | DONE | PASS |
| ENGINE-019 | PII & Data Hygiene | DONE | PASS |
| ENGINE-020 | Temperature, KPIs & Budgets | DONE | PASS |
| ENGINE-021 | Nexus & Datasets | DONE | PASS |
| ENGINE-022 | SEOUTM & Event Logging | DONE | PASS |

---

## D. Parking Lot / Future Engines

- **Scene Engine Animations:** Add support for describing smooth transitions for camera and nodes when the scene layout changes.
- **Scene Engine Live Updates:** Implement SSE or WebSocket support to push partial updates to clients for dynamic scenes.
- **Scene Engine Advanced Projection:** Enhance the `"vector_explorer"` recipe with more advanced dimensionality reduction techniques (e.g., UMAP, t-SNE).
- **BBK Studio Recipes:** Develop recipes specific to the BBK Studio, such as arranging stems, loops, and effects in a 3-D DAW-like interface.
- **Shop Layout Recipes:** Develop recipes for e-commerce, such as dynamic product walls, KPI dashboards, and interactive funnels.

---
# NEW PLANS
---

### PLAN-023: SQUARED OS v0 – CORE INFRA & ENGINES (NO APP LOGIC)

Status: DONE
Owner: Gem (Planner)
Last updated: 2025-12-01

**Goal**: To establish the core infrastructure and connect the essential "brain" engines of the SQUARED OS. This phase focuses purely on the foundational plumbing, with no application-specific behavior. The OS should be able to process a request, apply guardrails, interact with data, and log events securely.

---

#### Phase 0 – Lock contracts, not logic

**Goal**: Contracts and shapes are stable enough that infra work isn’t wasted. No app behaviour defined yet. No app logic in engines.

**Tasks**:
- **Task 0.1**: Confirm and document the canonical shapes for: Surface, App, Federation, Cluster, Gang, Agent.
- **Task 0.2**: Re-state the rule: Engines handle structure, routing, storage, and external calls. Agents (LLM calls + manifests) handle behaviour and judgement.
- **Task 0.3**: Mark which engines are required for OS v0. The required engines are:
    - `ENGINE-017` – Chat surface engine
    - `ENGINE-018` – Guardrails engine (Strategy Lock + 3-Wise)
    - `ENGINE-019` – PII/Data hygiene engine
    - `ENGINE-020` – KPI/Budget state + Temperature trigger engine
    - `ENGINE-021` – Nexus & datasets engine
    - `ENGINE-022` – SEO/UTM/Event logging engine
    - Any minimal ingest/log helpers required.
- **Task 0.4**: Mark all other engines as `NOT_REQUIRED_FOR_OS_V0` in a central registry (e.g., `engines/registry/engine_registry.json` with a status flag).
- **Task 0.5**: Ensure any “Temperature engine” or “CEO engine” does not contain behaviour. Temperature classification must be done by a Temperature agent (LLM call) using Nexus data + language definitions. A CEO view must be a combination of a Nexus space for “CEO signals”, a layout template, and a CEO ranking agent (LLM), not an engine.

**Implementation Notes for Max**:
Do not modify any engine to add app-specific behaviour. Engines only know about surfaces, tenants, cards, Nexus, events and external services.

---

#### Phase 1 – Core infra & secrets (GCP + AWS)

**Goal**: One solid backbone so engines have real services to talk to. This is infra + configuration only, still no app behaviour.

**Tasks**:
- **Task 1.1 (GCP)**: Ensure Vertex/LLM endpoints are available for: a generic chat/orchestrator agent, Temperature agent, CEO view agent, and helper agents (PII/UTM/SEO, etc.).
- **Task 1.2 (GCP)**: Define GSM (Google Secret Manager) keys for: Vertex/LLM access, and any other core secrets needed by engines.
- **Task 1.3 (GCP)**: Ensure there is a Cloud Run base service (or equivalent) for engines, with a single network and a single service account with only required permissions.
- **Task 1.4 (AWS)**: Confirm that one AWS account/OU is set up with a primary region.
- **Task 1.5 (AWS)**: Define S3 buckets for: raw uploads, datasets, and exports.
- **Task 1.6 (AWS)**: Define a database for Nexus metadata/state (e.g., RDS Postgres or DynamoDB).
- **Task 1.7 (AWS)**: Define a logging destination (e.g., CloudWatch log group).
- **Task 1.8 (AWS)**: Define IAM roles for: engines, admin, and read-only access.
- **Task 1.9 (Secrets)**: Ensure all coordinates (DB URLs, bucket names, etc.) come from GCP Secrets (GSM) or AWS Secrets (SSM/Secrets Manager).

**Implementation Notes for Max**:
When wiring engines, always read configuration from secrets or environment variables. Never hard-code ARNs, project IDs, or bucket names in engine code.

---

#### Phase 2 – Plumb the “core brain” engines (no media, no app behaviour)

**Goal**: For one test tenant + one surface, the OS can: accept chat, call LLM with manifests, read/write to Nexus, compute Temperature via agent, apply Guardrails via agent, and log events safely.

**Tasks**:
- **Task 2.1 (Chat surface engine)**:
    - Wire to the chosen LLM endpoint.
    - Add basic auth (API key/JWT is enough for v0).
    - Connect to a conversation state store (e.g., Redis, Postgres, Firestore).
    - Make it read from cards to know which surface/app/federation/agent is being invoked and which Nexus spaces are relevant.
    - Ensure it can stream tokens back to the UI (Decision needed: SSE or WebSocket).
- **Task 2.2 (Nexus & datasets engine)**:
    - Back Nexus by the real DB chosen in Phase 1.
    - Implement minimal, generic operations: `write_snippet`, `write_event`, `query_by_tags`, `query_for_agent`.
    - Namespace by tenant + surface and by space (style/data/research/state etc.), not by app.
- **Task 2.3 (KPI/Budget state + Temperature trigger engine)**:
    - Store KPI snapshots and budget bands in Nexus.
    - Provide methods to: update KPI state, retrieve current KPI state, call the Temperature agent (LLM) with KPI state + language definitions.
    - Persist `temperature_band` + explanation back to Nexus.
    - The engine must not contain formulas or thresholds; it only orchestrates storage and LLM calls.
- **Task 2.4 (Guardrails engine)**:
    - **Strategy Lock**: Given a proposed action + surface policies, call LLM to build a plan/summary and identify risks. Store “plan objects” in a `strategy_lock` Nexus space.
    - **3-Wise**: Call multiple LLM prompts/models, aggregate critiques, and store results in Nexus.
- **Task 2.5 (PII & Data hygiene engine)**:
    - Implement PII detection/masking via regex/heuristics for email, phone, address, order IDs, etc.
    - This engine wraps around anything being written into logs, Nexus history, or outbound events.
- **Task 2.6 (SEO/UTM & Event logging engine)**:
    - Provide a `log_event` function that calls the PII engine, enriches with UTM/SEO context, and ships structured events to the logging backend from Phase 1.
    - The engine must be generic, with fields like tenant, surface, engine, severity, payload.

---

#### Phase 3 – Generic app wiring test (still no behavioural definitions)

**Goal**: Prove that the OS slice can support any future app without changing engine code.

**Tasks**:
- **Task 3.1**: Define one simple placeholder App card that only defines which surface it belongs to, which federations/agents it would use, which Nexus spaces it touches, and which events it might emit.
- **Task 3.2**: Define one placeholder Federation that can call the Chat surface, read/write to Nexus, trigger Temperature/Guardrails, and emit a generic event.
- **Task 3.3**: Confirm that with the placeholder app/federation card in place, engines 017-022 can support the flow without any engine code referring to specific app semantics.

---

#### Phase 4 – Harden & extend (after OS v0 is proven)

**Goal**: Harden the OS and prepare for extension.

**Tasks**:
- **Task 4.1 (Harden)**: Implement robust logging, metrics, autoscaling, retries, and back-pressure.
- **Task 4.2 (Extend)**: Connect media engines (ASR, video, etc.), add new Nexus spaces as needed, and prepare for app-level card definitions.
- **Task 4.3 (Rule)**: Explicitly state that no app behaviour may be implemented in engines without a corresponding app/federation card defined first. Behaviour always lives in language cards + agents, never hard-coded.

---

**Execution rules**:
- **Planners (Gem)**: Mark new entries and tasks as `PENDING`.
- **Implementers (Max)**:
    - Set status to `ACTIVE` when starting work.
    - Log problems and solutions in the single log file with `PLAN_ID`.
    - Set status to `DONE` when finished, adding notes and artefact locations to the log.

Completed: 2025-12-01 – Repo-side deliverables created (contracts doc, infra/secret specs, registry OS v0 status map, placeholder app/federation cards, hardening notes). Engine code unchanged; external infra remains to be provisioned.

---
### PLAN-024: Universal Chat & Transports v0 (Repo-only)

Status: DONE
Owner: Max
Planner: Gil
Last updated: 2025-12-01

**Goal**: To prepare the repository for a universal chat system with multiple transport layers (HTTP, WebSocket, SSE). This is a "repo-only" task, meaning no external infrastructure, LLMs, or databases should be provisioned or connected. It is about setting up the contracts and stubs for a front-end to build against locally.

---

#### Phase 0 - Contracts & Stubs

**Goal**: Define stable contracts and implement stubbed, in-memory transport layers.

**Tasks**:
- **Task 0.1: Define Data Contracts**:
    - Implement Pydantic (or similar) schemas for `Thread`, `Message`, and `Contact`.
    - These contracts should be neutral and application-agnostic.
    - Location: `engines/chat/contracts.py` (or a suitable new location).

- **Task 0.2: Implemment Stubbed HTTP Transport**:
    - Create a FastAPI service with stubbed endpoints:
        - `GET /chat/threads`
        - `POST /chat/threads`
        - `GET /chat/threads/{id}/messages`
        - `POST /chat/threads/{id}/messages`
    - Use an in-memory dictionary for data storage.
    - The `POST /.../messages` endpoint should trigger a hardcoded agent echo reply.
    - Location: `engines/chat/service/http_transport.py`

- **Task 0.3: Implement Stubbed WebSocket Transport**:
    - Create a WebSocket endpoint: `/ws/chat/{thread_id}`.
    - It should handle `join` and `message` events from the client.
    - It should broadcast messages to all subscribers on a thread using an in-memory manager.
    - Location: `engines/chat/service/ws_transport.py`

- **Task 0.4: Implement Stubbed SSE Transport**:
    - Create an SSE endpoint: `/sse/chat/{thread_id}`.
    - It should send a `message` event whenever a new message is added to the thread from any transport.
    - Location: `engines/chat/service/sse_transport.py`

- **Task 0.5: Implement Transport Abstraction**:
    - Create a simple pub/sub abstraction that the HTTP, WebSocket, and SSE transports can use to communicate.
    - e.g., `publish_message(thread_id, message)` and `subscribe_to_thread(thread_id, callback)`.
    - This allows a message posted to the HTTP endpoint to be broadcast to WebSocket and SSE clients.
    - Location: `engines/chat/service/transport_layer.py`

- **Task 0.6: Add Tests & Documentation**:
    - Add basic unit/integration tests for the contracts and each transport layer.
    - Create a `README.md` inside the `engines/chat` directory explaining that this is a stub implementation for local development.

**Implementation Notes for Max**:
- All work is repo-only. Do not add any cloud dependencies or external service calls.
- All data is transient and stored in-memory.
- Clearly mark stubbed logic (e.g., agent replies) with code comments.
- Follow the existing conventions for file structure and testing.

---
### PLAN-025: CAIDENCE² Engine Readiness

**!!!--- PRODUCTION IMPLEMENTATION ---!!!**
**NOTE: THIS IS A PRODUCTION PLAN. ALL WORK MUST BE PRODUCTION-READY. NO STUBS ARE PERMITTED. ALL CONNECTIONS TO SERVICES (LLMS, DATABASES, APIS) MUST BE REAL AND USE THE PRODUCTION CONFIGURATIONS AND SECRETS. THIS IS A GO-LIVE PLAN.**
**!!!--- PRODUCTION IMPLEMENTATION ---!!!**

Status: DONE
Owner: Max
Planner: Gil
Last updated: 2025-12-01
AREA: engines

WORKING_NOTE (2025-12-05 16:29 GMT): Starting CAIDENCE² readiness review; will draft engine mapping doc and note gaps before proceeding to production tasks.
NOTE (2025-12-05): Phase 1 mapping drafted in docs/caidence2/engine_mapping.md; phases 2-3 pending production validation.

**Goal**: Make existing engines usable for the CAIDENCE² application by ensuring they are properly integrated and configured, without adding any application-specific logic into the engines themselves. All behavior must be driven by cards from the ADK.

---

#### Phase 1 – Engine Inventory for CAIDENCE² Needs

**Goal**: Map existing engines to CAIDENCE² functional roles and identify any gaps.

**Tasks**:
- **Task 1.1**: Create a mapping document (`docs/caidence2/engine_mapping.md`) that inventories existing engines against these required roles:
    - Chat surface / orchestrator
    - Nexus read/write
    - PII strip / Data hygiene
    - Guardrails (Strategy Lock + 3-Wise LLM)
    - Temperature / KPI band engine
    - SEOUTM & logging
- **Task 1.2**: In the mapping document, mark each engine's status:
    - **Ready**: Can be used as-is.
    - **Needs IO Tweak**: Requires minor adjustments to its input/output contracts.
    - **Needs Adapter**: Requires a thin adapter layer to be compatible.

---

#### Phase 2 – Chat Engine / Streaming Readiness

**Goal**: Ensure the main chat engine can serve CAIDENCE² requests and stream responses.

**Tasks**:
- **Task 2.1**: Verify the chat surface engine correctly handles requests specifying `app_id: 'caidence2'` and a valid `tenant_id`.
- **Task 2.2**: Confirm that the engine can stream responses via Server-Sent Events (SSE) and is designed in a way that a WebSocket bridge could be added later without a major refactor.
- **Task 2.3**: Ensure that all prompts and operational parameters are derived from a card-based manifest passed from the ADK, with no hard-coded prompts in the engine.

---

#### Phase 3 – Nexus Engine for CAIDENCE²

**Goal**: Ensure the Nexus engine can manage CAIDENCE² data spaces.

**Tasks**:
- **Task 3.1**: Verify the Nexus engine can correctly read from and write to the CAIDENCE² spaces as defined by the ADK. These spaces include:
    - `style_nexus`
    - `content_nexus`
    - `schedule_nexus`
    - `performance_nexus`
- **Task 3.2**: Confirm that all Nexus operations respect `tenant_id` and `app_id` for data isolation. Schemas for these spaces will be provided via cards.

---

#### Phase 4 – PII & Logging Integration

**Goal**: Ensure all data flowing through the system is properly logged and sanitized.

**Tasks**:
- **Task 4.1**: Verify the PII engine can reliably strip or mask sensitive information (emails, names, addresses) from the following data types: chat logs, schedule entries, and connector logs.
- **Task 4.2**: Confirm the central logging engine correctly accepts `DatasetEvent` entries for all relevant CAIDENCE² events, including app-specific events, calls to external connectors (YouTube, Slack, etc.), and guardrail decisions.
- **Task 4.3**: Ensure all data is passed through the PII filter before being persisted to any log or database.

---

#### Phase 5 – Guardrails & Temperature Integration

**Goal**: Integrate the decision-making and risk-assessment engines.

**Tasks**:
- **Task 5.1**: Ensure the Strategy Lock and 3-Wise LLM guardrail engines are callable by CAIDENCE² federations via the ADK, with no direct coupling.
- **Task 5.2**: The Temperature engine must be configured to:
    - Read KPI snapshots from the `performance_nexus`.
    - Call the designated LLM agent to assign a temperature band (`cold`, `sweet_spot`, `hot`).
    - Write the resulting temperature band and rationale back into the `performance_nexus`.

---

#### Phase 6 – Connector IO Contracts

**Goal**: Define the data contracts for external service connectors that CAIDENCE² will use.

**Tasks**:
- **Task 6.1**: Define and create the Pydantic schema files for the following connector IO contracts (request/response shapes):
    - `YOUTUBE.POST.CONTENT_V1`
    - `SLACK.SEND.MESSAGE_V1`
    - `KLAVIYO.ADD.TO_LIST_V1`
    - `ICAL.FEED.UPDATE_V1`
- **Task 6.2**: Register these new IO contracts in the engine/connector registry so they can be referenced by ADK cards. Note: This task is for defining the schemas only; implementation will occur in the connectors repository.

---

#### Phase 7 – Final Review: No App Logic in Engines

**Goal**: Guarantee the separation of concerns between engines and application logic.

**Tasks**:
- **Task 7.1**: Conduct a final review of all modified engine code to ensure no CAIDENCE²-specific logic (e.g., "what to post," "when to post") has been hard-coded.
- **Task 7.2**: Confirm that all such behavioral logic resides exclusively in the cards and orchestration layer managed by the ADK.
---

Completion Notes (2025-12-05):
- Created Phase 1 engine mapping at docs/caidence2/engine_mapping.md with roles/status and identified adapter needs.
- Phase 2–7 production validation not performed in this pass; requires real environments/configs. Follow-up needed before go-live.
### PLAN-026: CHAT_NEXUS_VERTEX_PROD_WIRING_DEV

**!!!--- PRODUCTION WIRING ---!!!**
**NOTE: THIS IS A PRODUCTION-MODE PLAN FOR THE 'northstar-os-dev' ENVIRONMENT. NO STUBS. NO ECHO AGENTS. ALL SERVICES AND BACKENDS (GCP, FIRESTORE, ADK/VERTEX) MUST BE REAL.**
**!!!--- PRODUCTION WIRING ---!!!**

Status: DONE
Summary: Wire chat transports to real LLM (Vertex), Nexus (Firestore), and GCS buckets using GSM secrets for Tenant 0. No stubs.
Agent: Max
Scope: CAIDENCE² dev vertical slice – Chat + Nexus + Media, wired to ADK (no external connectors)
Reference Tenant: `t_northstar-dev` (from GSM `northstar-dev-tenant-0-id`)

---

**✅ Goal**
- For tenant `t_northstar-dev`, we want:
- Real chat via ADK/Vertex (no echo stubs).
- A real blackboard per conversation stored in Nexus/Firestore.
- Real media ingest:
    - Upload from the UI → GCS raw bucket via engines.
    - Metadata persisted into Nexus/Firestore so the UI “stack” can list and display items.
- All of this running as a Cloud Run service using the existing `northstar-dev-engines` service account and GSM secrets.
- No external connectors yet (no YouTube/Slack/Klaviyo).

---

**📂 1. Environment + Config**

- **1.1**: Define or update an engine config file (e.g., `engines/config/env_dev.py`) that:
    - Reads:
        - `TENANT_ID` from GSM secret `northstar-dev-tenant-0-id`
        - `RAW_BUCKET` from GSM secret `northstar-dev-raw-bucket`
        - `DATASETS_BUCKET` from GSM secret `northstar-dev-datasets-bucket`
        - `NEXUS_BACKEND` from GSM secret `northstar-dev-nexus-backend`
    - Uses Application Default Credentials (ADC) for auth, no API keys.
    - Exposes a simple `get_settings()` function that other engines can import.
- **1.2**: Add a small doc: `docs/infra/ENGINES_DEV_RUNTIME.md` that explains:
    - How engines discover the runtime environment:
        - Project ID: `northstar-os-dev`
        - Region: `us-central1`
        - Service Account: `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`
    - That for dev, we assume Cloud Run + Firestore + GCS, all authenticated via ADC.

---

**🧱 2. Nexus Persistence (Firestore)**

- **2.1**: Implement a Nexus backend adapter if one does not already exist (e.g., `engines/nexus/backends/firestore.py`) that:
    - Uses Firestore Native in `us-central1`.
    - Can:
        - `write_snippet(tenant_id, space, payload)` – stores a document.
        - `write_event(tenant_id, event)` – stores `DatasetEvents`.
        - `query_by_tags(tenant_id, space, tags, limit)` – minimal filter.
    - Uses `t_northstar-dev` as the tenant in dev, but never hardcodes it in the functions; it must always be passed in via context.
- **2.2**: Wire the existing Nexus contracts to this backend so that any new chat session, media upload, or auto-generated content preview writes at least one Nexus snippet and one `DatasetEvent`.

---

**💬 3. Universal Chat (PLAN-024 follow-up, no stubs)**

- **3.1**: Take the existing chat contracts + transports from `engines/chat/` and remove/retire the “agent echo” stub behavior.
- **3.2**: Implement a real processing pipeline: `HTTP/WS/SSE → chat service → ADK/Vertex call → Nexus write → streamed response`.
- **3.3**: Implement an ADK/Vertex client layer (e.g., `engines/chat/service/llm_client.py`) that:
    - Uses ADC to call Vertex AI (Gemini is fine).
    - Accepts `tenant_id`, an `agent_manifest` (from cards), `conversation_history` (from Nexus), and `blackboard_state`.
    - Returns a streaming iterator of tokens for the SSE/WebSocket transports to forward to the client.
- **3.4**: Wire the transports for real use:
    - **HTTP**: Simple “send message, get complete reply”.
    - **WebSocket + SSE**: Proper streaming of tokens from the ADK call to the client.

---

**🎞 4. Media Ingest + Stack Listing**

- **4.1**: Implement a media ingest endpoint (e.g., `POST /media/upload`) in the main engines API that:
    - Accepts a multipart upload containing the file, `tenant_id`, and optional tags.
    - Writes the file to the `RAW_BUCKET` (`gs://northstar-os-dev-northstar-raw`) under the path: `<tenant_id>/media/<uuid>/<filename>`.
    - Writes a Nexus record to the `media` space with the payload: `{ tenant_id, asset_id, gcs_path, mime_type, tags, created_at }`.
    - Emits one `DatasetEvent` describing the upload.
- **4.2**: Implement a list endpoint (e.g., `GET /media/stack`) that:
    - Accepts `tenant_id` and optional filters.
    - Reads from the Nexus backend (not GCS) to return a list of recent media items for the UI to render.
- **4.3**: Add tests for upload → GCS write, upload → Nexus write, and that the stack listing returns what was written.

---

**🚀 5. Cloud Run Dev Deployment**

- **5.1**: Add or update a minimal Cloud Run deployment manifest (e.g., `deploy/dev/engines-chat.yaml`) that:
    - Deploys the chat + media service as a single container.
    - Uses the service account `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`.
    - Sets required environment variables for `GCP_PROJECT_ID`, `GCP_REGION`, and any GSM secret names.
- **5.2**: Add a short deployment script (e.g., `deploy/dev/deploy_chat.sh`) that runs `gcloud run deploy ...` with the correct flags and the manifest.

---

**🧾 6. Logging & PII Hygiene**

- **6.1**: Ensure the chat and media endpoints use the PII/Data Hygiene engine before writing any logs or Nexus records.
- **6.2**: Ensure a `DatasetEvent` is shipped into the logging engine for each chat turn and each media upload.
- **6.3**: Update the canonical log file (`docs/logs/ENGINES_LOG.md`) with:
    - What changed.
    - Where the new endpoints live.
    - Any final bash commands required to finish infrastructure setup (if anything was discovered to be missing).

---
Max: mark this PLAN as DONE when all tasks are complete and log your work in the canonical log.

Completed: 2025-12-02 – Added Vertex-backed chat pipeline hook, media upload/list endpoints with Nexus/logging, Cloud Run manifest/script, and dev runtime configuration docs.
---
### PLAN-025: INFRA_DEV_BASELINE

Status: DONE
Owner: Gil
Implementer: Max
Last updated: 2025-12-01

**Goal**: Lock northstar-os-dev dev infra, engines SA, Firestore Nexus, GCS buckets, GSM secrets.

**Details**
- Project: `northstar-os-dev`
- Region: `us-central1`
- Service Account: `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`
- Nexus backend: Firestore (native, us-central1)
- GCS buckets: `gs://northstar-os-dev-northstar-raw`, `gs://northstar-os-dev-northstar-datasets`
- GSM secrets: `northstar-dev-tenant-0-id`, `northstar-dev-raw-bucket`, `northstar-dev-datasets-bucket`, `northstar-dev-nexus-backend`
- Required roles on engines SA: `roles/secretmanager.secretAccessor`, `roles/storage.objectAdmin`, `roles/run.invoker`, `roles/aiplatform.user`

Completed: 2025-12-01 – Baseline documented in INFRA_GCP_DEV.md; anti-drift rules added to Constitution.

### PLAN-027 – Temperature Plans & Weighting Pattern (NEW)

- **Status**: DONE
- **Goal**: Formalise temperature weighting via Nexus plans; engines stay deterministic.
- **Work**:
  - Define `TemperatureWeightsPlan` schema (tenant/env/weights/note/version).
  - Temperature engine loads latest plan from Nexus (Firestore) with defaults if none.
  - Add service entrypoint to measure temperature: load plan → run engine → log DatasetEvent (kind `temperature_measurement`).
  - Firestore backend helper to fetch latest plan per tenant/env from `temperature_plans_{TENANT_ID}`.
  - Doc the pattern (LLM/DS clusters write plans; engines read only).
  - Tests for default vs planned weights and Nexus helper.
- **WORKING_NOTE (2025-12-05 15:02 GMT)**: Drafting TemperatureWeightsPlan schema and deterministic measurement pattern; updating docs/constitution/TEMPERATURE_PLANS.md and engine notes.
- **Completion Notes (2025-12-05)**:
  - Defined TemperatureWeightsPlan schema with versioning/defaults and Firestore collection conventions in docs/constitution/TEMPERATURE_PLANS.md.
  - Documented deterministic runtime flow (load approved plan → run engine → emit temperature_measurement DatasetEvent) with fallback defaults.
  - Captured planning job path, Strategy Lock triggers for risky changes, and helper/test expectations for plan selection and logging.

### PLAN-028 – Font Helper & Registry (NEW)

- **Status**: DONE
- **Goal**: Provide font/preset tokens for variable fonts (e.g., Roboto Flex) from a registry.
- **Work**:
  - Define font config/preset schemas (font_id, display_name, css_family_name, tracking bounds, presets).
- Registry helper to load fonts (starting with Roboto Flex JSON), fetch preset, clamp tracking, and emit CSS tokens (`fontFamily`, `fontVariationSettings`, `letterSpacing`).
- Docs describing card usage: apps reference font_id + preset_code + tracking; engines return tokens.
- Tests for unknown font/preset, tracking clamp, stable token generation.
- **WORKING_NOTE (2025-12-05 15:02 GMT)**: Starting font registry/helper planning; will define schemas and usage notes in FONT_REGISTRY doc.
- **Completion Notes (2025-12-05)**:
  - Documented font registry entry schema, tracking bounds, and presets in docs/engines/FONTS_HELPER.md.
  - Defined helper flow for font/preset lookup, tracking clamp, and deterministic token emission (fontFamily/fontVariationSettings/letterSpacing).
  - Captured test expectations for unknown font/preset, clamping, and stable outputs; initial registry location noted for Roboto Flex JSON.

### PLAN-029 – PLAN-TEMP-REFINE (Temperature weighting + review loop)

- **Status**: DONE
- Define planning vs runtime: runtime temperature measurement reads latest approved plan only; planning job drafts proposals and writes after review.
- Extend TemperatureWeightsPlan (proposed_by, notes, status/version) and store in Firestore `temperature_plans_{TENANT_ID}`.
- Add review/apply helper that reads TemperatureState/KPI history, runs Strategy Lock, and writes approved plans.
- Keep measurement path LLM-free; LLM/DS clusters act only in the planning job.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Expanding TEMPERATURE_PLANS doc with review loop, plan status/version rules, and planning job helper expectations.
- **Completion Notes (2025-12-05)**:
  - Added planning job flow with draft→review→approved lifecycle, Strategy Lock triggers, and supersede pointers in docs/constitution/TEMPERATURE_PLANS.md.
  - Documented version/status rules for TemperatureWeightsPlan and clarified runtime read-only path vs planning writer path.
  - Captured helper expectations for plan fetch/diff and test coverage for defaults/version selection/dataset events.

### PLAN-030 – PLAN-CHAT-ROUTING (multi-scope chat routing + blackboards)

- **Status**: DONE
- Add chat scope schema (surface/app/federation/cluster/gang/agent) carried with messages.
- Pipeline persists scope to Nexus/logging and routes to appropriate orchestration stub (surface/app default; scoped routes annotated).
- Tests assert scoped messages appear with scope metadata in Nexus/logging.
- Document scheduled vs on-demand vs reactive distinctions in chat README.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Drafting chat scope schema and logging/routing notes; updating chat README/TILES wiring as needed.
- **Completion Notes (2025-12-05)**:
  - Extended chat scope schema to carry surface/app/federation/cluster/gang/agent plus legacy kind/target in `engines/chat/contracts.py`.
  - Pipeline now logs all scope dimensions to Nexus tags and DatasetEvents with `exclude_none` scope payloads.
  - Updated `engines/chat/README.md` to document scope shape and routing/logging expectations.

### PLAN-031 – PLAN-REACTIVE-CONTENT (DatasetEvent-driven reactive plays)

- **Status**: DONE
- Introduce reactive watcher that consumes DatasetEvents (e.g., content.published.youtube_video) and emits follow-up content.reactive.* events via logging/Nexus.
- Provide hook point for connectors/ingest to trigger watcher.
- Document reactive triggers vs scheduled vs chat triggers; tests for reactive generation.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Documenting reactive watcher contract and trigger paths in docs/engines/REACTIVE_CONTENT.md.
- **Completion Notes (2025-12-05)**:
  - Expanded reactive watcher contract in docs/engines/REACTIVE_CONTENT.md with trigger types, event shapes, and hook expectations.
  - Documented DatasetEvent inputs/outputs and refs/trace propagation for reactive plays; tests noted for future coverage.

### PLAN-032 – PLAN-STRATEGY-LOCK-ACTIONS (action classification)

- **Status**: DONE
- Classify actions requiring Strategy Lock (+ optional 3-wise) vs those that do not.
- Apply classification to temperature planning job (planning path guarded; runtime measurement not user-facing).
- Document action list for OS/enterprise layer; keep engine keyword logic pluggable.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Updating STRATEGY_LOCK_ACTIONS.md with action classifications and temperature planning guardrail notes.
- **Completion Notes (2025-12-05)**:
  - Updated docs/constitution/STRATEGY_LOCK_ACTIONS.md with canonical lists of actions requiring Strategy Lock/3-Wise/HITL versus exempt actions.
  - Added guardrails linking firearms risk levels and temperature planning (risk increases) to Strategy Lock triggers.
  - Clarified drafting/runtime reads as non-guarded paths and noted pluggable keyword policy.

### PLAN-0AA – Manifest & Token Graph Contract

- **Status**: DONE
- **Area**: infra/ui-manifests
- **Goal**: Define the canonical JSON/typed shape for manifests, content slots, and tokens (typography/layout/colour/behaviour) across apps/surfaces.
- **Scope**:
  - Path/ID conventions for components, content slots, and token domains.
  - How atoms/views/sections map into the manifest graph; defaults vs current values.
  - Separation of content vs tokens; patch addressing rules.
- **Non-Goals**:
  - No storage/DB or API implementation.
  - No UI or agent wiring; contracts only.
- **Artefacts**:
  - docs/constitution/MANIFEST_TOKEN_GRAPH.md
- **WORKING_NOTE (2025-12-05 14:48 GMT)**: Re-open contract to verify manifest/token graph definitions match PLAN-0AA scope; refine doc if gaps found.
- **Completion Notes (2025-12-05)**:
  - Re-established manifest graph contract covering surface/section/view/atom relationships and component ID rules in docs/constitution/MANIFEST_TOKEN_GRAPH.md.
  - Documented component/content/token path conventions and patch addressing shape for capability checks.
  - Expanded token domain shapes (typography/layout/colour/behaviour) plus inheritance/default merge rules vs live values.
  - Clarified metadata immutability and versioning expectations for manifest state.
- **Completion Notes (2025-12-02)**:
  - Confirmed manifest/token graph contract documented in MANIFEST_TOKEN_GRAPH.md with structure, paths, and separation of content vs tokens.
  - No code changes required; plan closed per instructions.

### PLAN-0AB – Cluster Capabilities & Scoped Patching

- **Status**: DONE
- **Area**: infra/agents/scopes
- **Goal**: Define capability descriptors for clusters/agents that constrain readable/writable paths and allowed ops; patch contract checked against capabilities.
- **Scope**:
  - Capability schema (allowed_reads/allowed_writes/allowed_ops, cluster metadata).
  - Patch contract (path/op/value, actor metadata) and validation rules.
  - Origin metadata (human/agent, cluster_id/agent_id) expectations.
- **Non-Goals**:
  - No ACL/auth implementation; no runtime validators yet.
  - No transport wiring.
- **Artefacts**:
  - docs/constitution/CLUSTER_CAPABILITIES.md
- **WORKING_NOTE (2025-12-05 14:52 GMT)**: Drafting capability descriptor schema and scoped patch contract in CLUSTER_CAPABILITIES.md aligned to manifest/token paths.
- **Completion Notes (2025-12-05)**:
  - Documented capability descriptor schema with cluster metadata, scopes, allowed_reads/writes, and allowed_ops in docs/constitution/CLUSTER_CAPABILITIES.md.
  - Added path globbing rules aligned to manifest content/token/metadata families to prevent cross-family writes.
  - Refined patch contract to use set/delete/merge ops with validation constraints and immutable root safeguards.
  - Clarified origin metadata expectations for humans/agents and audit/logging requirements.

### PLAN-0AC – Design Tools Scoping (Typography/Layout/Colour/Copy)

- **Status**: DONE
- **Area**: surfaces/design-tools
- **Goal**: Specialise manifest + capabilities model for creative tools (slides/canvas/video strips) with scoped clusters (typography/layout/colour/copy).
- **Scope**:
  - Representing layers/slides/clips within the manifest graph.
  - Cluster examples for tool families and their allowed paths.
  - Interaction model hints for patching (tokens vs content slots) in creative tools.
- **Non-Goals**:
  - No UI or engine code; no connector/model choices.
- **Artefacts**:
  - docs/constitution/DESIGN_TOOLS_SCOPING.md
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Updating DESIGN_TOOLS_SCOPING.md with manifest representations, cluster scopes, and patching hints for creative tools.
- **Completion Notes (2025-12-05)**:
  - Expanded design-tool manifest examples (slides/layers/clips) with slots and token domains in docs/constitution/DESIGN_TOOLS_SCOPING.md.
  - Documented cluster scopes for typography/layout/colour/copy/media and enforcement rules via capabilities.
  - Added interaction hints (movement, louder headline, timeline trims, palette usage) and locking/pinning notes.

### PLAN-0AD – Tiles registry & payload schema

- **Status**: DONE
- **Area**: surfaces/tiles
- **Summary**: Define extensible tile types and payload fields (id/type/size_hint/strategy_lock_state/actions/timestamps/Nexus refs/pinned) aligned to the manifest/token graph.
- **Detail**:
  - Add tile schema doc; specify registry location and type codes; enforce tight masonry (size_hint is a visual weight, not layout gaps).
  - Tiles carry content refs (Nexus snippets/events, external feed refs) and do not mutate tokens; align with manifest/token graph for UI consumption.
  - Capture minimum mix guidance (KPI + deep content + strategy/next-step) and extensibility for future tile types/sizes.
- **Artefacts**:
  - docs/constitution/TILES_SURFACE.md
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Expanding TILES_SURFACE.md with tile schema, registry notes, size_hint rules, and Strategy Lock fields.
- **Completion Notes (2025-12-05)**:
  - Added tile registry/type guidance, payload schema, size_hint semantics, and Strategy Lock/action handling in docs/constitution/TILES_SURFACE.md.
  - Documented content/Nexus refs vs external refs, cta refs preference, and manifest alignment (no token mutations).
  - Included mix guidance (KPI + deep content + strategy) and pinned/order behaviour for UI consumption.

### PLAN-0AE – CEO LLM tile-orchestration contract

- **Status**: DONE
- **Area**: infra/agents/tiles
- **Summary**: Specify how the CEO agent reads Nexus/feeds and emits a ranked tile list—no tile engine math.
- **Detail**:
  - Define request/response contract (inputs: tenant/env/context/filters; outputs: ordered tiles with rationale/trace, Strategy Lock state carried through).
  - Data sources: Nexus snippets/events, external feeds, Strategy Lock status; CEO cluster composes payloads only, respecting cluster capabilities (no direct token writes).
  - Open questions: cadence/trigger model (pull vs push), maximum tile count, rationale retention.
- **Artefacts**:
  - docs/constitution/TILES_SURFACE.md
  - docs/infra/TILES_WIRING.md
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Updating TILES_WIRING.md with CEO agent request/response, data sources, and trigger/cadence notes.
- **Completion Notes (2025-12-05)**:
  - Added CEO agent request/response contract, data sources, Strategy Lock integration, and triggers/cadence notes in docs/infra/TILES_WIRING.md.
  - Captured API surface (HTTP/WS), dataset event logging, and strategy_lock_state caching/revalidation considerations.
  - Reiterated manifest alignment (no token writes) and limits/pagination open questions.

### PLAN-0AF – Tiles API surface for UI

- **Status**: DONE
- **Area**: infra/apis
- **Summary**: Define HTTP/WS contract for requesting tiles (tenant/env/auth) returning PLAN-0AD payloads.
- **Detail**:
  - Specify endpoints/params (e.g., GET /tiles?tenant=...&env=...&surface=...&limit=...; WS/SSE shape if used) and auth expectations.
  - Responses must expose tile payloads (size_hint, strategy_lock_state, actions) without surface grouping in the first view.
  - Open questions: pagination vs cursor, cache headers/ETags, anonymous access (likely none).
- **Artefacts**:
  - docs/infra/TILES_WIRING.md
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Aligning Tiles API contract and auth/caching notes in TILES_WIRING.md; documenting WS/SSE shape.
- **Completion Notes (2025-12-05)**:
  - Expanded TILES_WIRING.md with HTTP/WS params, response shape, auth/errors, caching/ETag notes, and strategy_lock_state revalidation guidance.
  - Documented tenant/env query requirements, limits, cursor/pagination expectations, and rationale/trace handling.

### PLAN-0AG – Strategy Lock integration in tiles

- **Status**: DONE
- **Area**: guardrails/strategy-lock
- **Summary**: Define how tiles carry Strategy Lock/3-Wise state and auto-action eligibility.
- **Detail**:
  - Enumerate tile fields for lock status (pending/allowed/blocked), icon hints, and auto-action suggestions (only when pre-cleared).
  - Map to existing Strategy Lock action classifications; no new policy engine; clarify partial approvals/TTL expectations.
  - Open questions: state caching, per-tile action scoping, how to represent “pending review” in UI tokens.
- **Artefacts**:
  - docs/constitution/TILES_SURFACE.md
  - docs/constitution/STRATEGY_LOCK_ACTIONS.md (xref)
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Documenting tile lock fields, TTL/caching, and action eligibility with xrefs to Strategy Lock classifications.
- **Completion Notes (2025-12-05)**:
  - Documented tile lock fields, TTL/revalidation expectations, and action eligibility in docs/constitution/TILES_SURFACE.md.
  - Reiterated per-tile action scoping and cross-ref to Strategy Lock classifications for risky actions.

### PLAN-0AH – Logging & Nexus events for tiles

- **Status**: DONE
- **Area**: logging/nexus
- **Summary**: Define DatasetEvent shapes for tile composition, impressions, clicks, and actions.
- **Detail**:
  - Event types (e.g., tiles.composed, tile.impression, tile.action) with required fields: tile_id, type, size_hint, strategy_lock_state, action_ref, timestamps, pinned, order index.
  - Storage expectations in Nexus/Firestore; CEO traces recorded without PII; align with manifest/token graph and cluster capabilities (logging only, no token mutation).
  - Open questions: sampling vs full fidelity, retention, linkage to blackboards and external feeds.
- **Artefacts**:
  - docs/infra/TILES_WIRING.md
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Adding DatasetEvent shapes for tiles composition/impression/action and retention notes in TILES_WIRING.md.
- **Completion Notes (2025-12-05)**:
  - Added DatasetEvent shapes for tiles.composed, tile.impression, and tile.action in docs/infra/TILES_WIRING.md with required fields.
  - Noted PII exclusion, Strategy Lock revalidation on actions, and retention/sampling open questions.

### PLAN-0AI – Firearms & HITL Groundwork

- **Status**: DONE
- **Area**: guardrails/firearms
- **Summary**: Define firearms classes, registry schema, tenant constitution switches, and how firearms interact with Strategy Lock/3-Wise/HITL.
- **Detail**:
  - Firearms conceptual model: OS constitution vs tenant constitution vs per-tool firearms metadata; initial firearms classes (outbound_email, outbound_social, outbound_web, spend_budget, destructive_data, etc.) kept extensible.
  - Firearms Registry schema: firearms_id, description, risk_level, requires_hitl, optional cooldown/pacing hints; referenced by tools/agents/tenant policies.
  - Interaction rules: licensing visibility, Strategy Lock + 3-Wise requirements when outside corridors; tenant-level overrides for when licence/HITL is needed.
  - Artefact: docs/constitution/FIREARMS_AND_HITL.md
- **WORKING_NOTE (2025-12-05 14:56 GMT)**: Updating FIREARMS_AND_HITL.md with registry schema, classes, and Strategy Lock/3-Wise/HITL interaction rules.
- **Completion Notes (2025-12-05)**:
  - Expanded firearms classes and registry schema (risk level, Strategy Lock default, HITL flag, cooldown) in docs/constitution/FIREARMS_AND_HITL.md.
  - Added tenant constitution overrides for licence/HITL/cooldown plus example entry and review metadata.
  - Linked tool/agent metadata to firearms classes and capability exposure rules.
  - Detailed Strategy Lock/3-Wise/HITL flow, cooldown enforcement, and DatasetEvent audit expectations.

### PLAN-0AJ – Tool Registry Groundwork

- **Status**: DONE
- **Area**: infra/tools
- **Summary**: Define a unified Tool Descriptor language for MCP/external APIs/internal engines/local helpers, including firearms metadata and cluster/gang scoping.
- **Detail**:
  - Tool Descriptor schema: tool_id, kind (external_mcp/internal_engine/http_api/local_helper), description, input/output schema refs, firearms_class link, cost_hint, allowed_clusters/gangs, optional rate limits.
  - Clarify how MCP fits vs internal engines/http APIs; routing is abstracted from agents.
  - Cross-link to manifest/token graph and cluster capabilities so clusters reference tools by tool_id with scoped permissions.
  - Artefact: docs/constitution/TOOL_REGISTRY.md
- **WORKING_NOTE (2025-12-05 14:57 GMT)**: Updating TOOL_REGISTRY.md with unified descriptor schema, firearms metadata, and cluster/gang scoping rules.
- **Completion Notes (2025-12-05)**:
  - Expanded Tool Descriptor schema with transport config, tenant/env scopes, cooldowns/rate limits, and cost hints in docs/constitution/TOOL_REGISTRY.md.
  - Clarified MCP/internal/http/local kinds with transport fields and routing expectations.
  - Added firearms linkage plus cluster/gang exposure rules and capability interplay.
  - Linked tool outputs back to manifest/token graph with capability-gated application.

### PLAN-0AK – Orchestrator Patterns (LLM + Rails)

- **Status**: DONE
- **Area**: infra/orchestration
- **Summary**: Define hybrid rails + LLM orchestrator pattern, hook points into guardrails/temperature, and a worked reactive use-case example.
- **Detail**:
  - Rails layer: triggers (scheduled/reactive), lifecycle (Draft→QA→Approved→Published), retries/backoff/dead-letter, enforcement of firearms/Strategy Lock/3-Wise/HITL.
  - Orchestrator-as-agent: reads blackboard/Nexus/preferences/temperature, Tool Registry, and decides cluster/tool calls; uses only registered tools.
  - Hook points to existing engines (Temperature, Strategy Lock/3-Wise, logging via DatasetEvent).
  - Example flow (blog from YouTube event) consistent with manifest/token graph and cluster capabilities; planning only—no endpoints or runtime wiring.
  - Artefact: docs/constitution/ORCHESTRATION_PATTERNS.md
- **WORKING_NOTE (2025-12-05 14:54 GMT)**: Updating ORCHESTRATION_PATTERNS.md with hybrid rails + LLM flow, guardrail hook points, and a reactive example.
- **Completion Notes (2025-12-05)**:
  - Expanded rails lifecycle with triggers, retries, dead-letter handling, and guardrail enforcement checkpoints in docs/constitution/ORCHESTRATION_PATTERNS.md.
  - Clarified orchestrator inputs (blackboard/Nexus/temperature/Tool Registry) and capability-gated tool calling with patch validation.
  - Added guardrail hook points for Temperature, Strategy Lock, 3-Wise, firearms/HITL, and DatasetEvent logging.
  - Documented reactive YouTube→blog flow showing dataset events, validated patches, QA loop, and publish gating.

---

### PLAN-CONNECTORS-SECRETS-V1 – Tenant IDs, Connector IDs, GSM Secrets

- **Status**: DONE
- **Owner**: Max
- **Area**: infra/naming
- **Summary**: Lock canonical patterns for tenant IDs, connector IDs, and GSM secret naming for OS-paid and BYOK connectors.
- **Detail**:
  - Add/refresh doc `docs/infra/CONNECTORS_SECRETS_NAMING.md` capturing:
    - Tenant ID pattern: `t_<slug>` (e.g., `t_northstar-dev`, `t_snakeboard-uk`).
    - Connector ID pattern: `conn.<provider>.<product>.<scope>` (e.g., `conn.vertex.gemini.core`, `conn.vertex.gemini.cheap`, `conn.bedrock.claude.core`, `conn.router.openrouter.core`).
    - GSM secret naming:
      - OS-paid key: `conn-<provider>-<product>-<scope>-key` (e.g., `conn-vertex-gemini-core-key`).
      - Per-tenant BYOK: `tenant-<tenant_id>-<provider>-<product>-<scope>-key` (e.g., `tenant-t_northstar-dev-vertex-gemini-core-key`).
  - Tasks to future self: audit for conflicting names; if divergence exists, document migration notes in the doc—never silently diverge.
  - Planning-only; no code changes in this pass.
- **WORKING_NOTE (2025-12-05 14:59 GMT)**: Refreshing CONNECTORS_SECRETS_NAMING.md with tenant ID/connector ID/GSM secret patterns and migration notes.
- **Completion Notes (2025-12-05)**:
  - Locked tenant_id and connector_id patterns with provider/product/scope guidance in docs/infra/CONNECTORS_SECRETS_NAMING.md.
  - Documented GSM secret naming for OS-paid vs BYOK plus suffix guidance for multi-secret connectors.
  - Added storage expectations (GSM only, DB metadata) and runtime resolution notes, retaining migration audit tasks.

### PLAN-TENANTS-AUTH-BYOK-V1 – Multi-tenant model, auth baseline, BYOK API

- **Status**: DONE
- **Owner**: Max
- **Area**: infra/tenants-auth
- **Summary**: Plan tenant/user models, auth baseline, and BYOK endpoints with PII-safe handling.
- **Detail**:
  - Tenant model (planning): table with `tenant_id (t_<slug>)`, `display_name`, `plan_tier (free/pro/enterprise)`, `billing_mode (os_paid/byok)`, `created_at`, `updated_at`.
  - User model (planning): table with `user_id`, `tenant_id`, `email`, `password_hash (bcrypt/argon2)`, `role (owner/admin/member)`, `display_name`, timestamps.
  - Auth baseline (planning): `/auth/register`, `/auth/login`; JWT signing key in GSM (`auth-jwt-secret`); passwords hashed only, never in GSM/logs.
  - BYOK API (planning): `POST /tenants/{tenant_id}/connectors/{provider}/{product}/{scope}/key` accepts `{api_key}`; stores secret in GSM (`tenant-<tenant_id>-<provider>-<product>-<scope>-key`), stores metadata only in DB (`has_byok`, `last_updated_at`, `masked_preview`). `GET /tenants/{tenant_id}/connectors` returns metadata only. Explicit: raw keys never in logs, Nexus, DatasetEvents.
  - PII/GDPR/UTM logging constraints: plan enforcement of PII engine around auth/BYOK/logs; include tests later to ensure keys/passwords never leak.
  - Planning-only; no implementation yet.
- **WORKING_NOTE (2025-12-05 15:00 GMT)**: Drafting tenant/user model + BYOK auth baseline in TENANTS_AUTH_BYOK doc with PII-safe handling.
- **Completion Notes (2025-12-05)**:
  - Added tenant/user model planning with roles, billing/plan fields, and PII handling in docs/infra/TENANTS_AUTH_BYOK.md.
  - Documented auth baseline (register/login) with GSM-held JWT secret and logging constraints.
  - Planned BYOK endpoints with GSM secret naming, metadata-only responses, and explicit no-logging of raw keys.
  - Captured PII/GDPR/UTM logging requirements and future redaction/test expectations.

### PLAN-V0-SUCCESS-SNAPSHOT – Multi-framework, multi-cloud, Caidence, tools

- **Status**: DONE
- **Owner**: Max
- **Area**: infra/runtime-overview
- **Summary**: Capture v0 success criteria across frameworks, clouds, models/APIs, and product targets.
- **Detail**:
  - Frameworks: LangGraph, Google ADK, Strands Agents, AgentCore.
  - Clouds: GCP + AWS primary; Oracle for 3D/video engines + model tuning.
  - Models/APIs: Vertex (Gemini/Veo/etc.), Bedrock models, cheap/router providers (Mistral, DeepInfra, etc.).
  - Success checklist (no implementation now):
    - Hello-world agent on ADK (Vertex); Strands + AgentCore (Bedrock); LangGraph (BYO keys).
    - Multi-agent orchestration tested across LangGraph + one other.
    - Full flow App → Federation → Cluster → Agent working.
    - WhatsApp-style chat surface tenant-ready.
    - 3D engine fully functional (back & front).
    - Caidence prod ready for tenants.
    - Bot Better Know (including 3D space) live.
    - 15 free “tools” (clusters) live on squared-agents.app.
    - GDPR / PII / UTM logs site-wide.
    - Stripe connected & live; GA4 connected site-wide; paid advertising live with tracking.
    - Dashboards reading live from Stripe, GCP, AWS, Google Ads (COGS/spend); MER, ROAS, Gross Profit wired.
    - UI builder “UltreX” live but invite-only.
  - Planning-only; used to drive future activation tasks.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Drafting success snapshot checklist doc summarising frameworks/clouds/models/product targets.
- **Completion Notes (2025-12-05)**:
  - Captured v0 success checklist across frameworks/clouds/models and product targets in docs/plan/V0_SUCCESS_SNAPSHOT.md.

### PLAN-AGENT-FLOW-VIEWER-V1 – Agent Flow Viewer requirements

- **Status**: DONE
- **Owner**: Max
- **Area**: surfaces/tooling
- **Summary**: Plan an Agent Flow Viewer per Jay’s spec for inspecting blackboards, orchestration, and logs.
- **Detail**:
  - Black-and-white only; App/Federation/Cluster/Agent blackboards with zoom.
  - Orchestration/vendor dropdowns per blackboard; timeline + “play” mode.
  - Logs wired to logging model (runs, steps, artefacts, stall points, etc.); cards integration (live card on click).
  - Drag-and-drop graph editor; nodes always backed by cards; simulation/shadow run hooks.
  - Dedicated debugging/analysis agent cluster + tenant-specific Nexus learnings.
  - Logging requirements: everything defined must be inspectable at this level.
  - Planning-only; implementation deferred.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Drafting Agent Flow Viewer planning doc covering blackboards, timelines, and card integration.
- **Completion Notes (2025-12-05)**:
  - Added planning doc docs/plan/AGENT_FLOW_VIEWER.md covering blackboards, timelines/playback, card integration, and graph editor requirements.

### PLAN-033 – NEXUS_VECTOR_ENABLEMENT

- **Status**: PENDING
- **Area**: infra/nexus
- **Summary**: Enable vector search for Nexus while keeping Firestore canonical.
- **Detail**:
  - Use Vertex AI Vector Search (us-central1) with metadata filters on tenant/env/kind; autoscale min=0 to control cost.
  - Embeddings: Vertex text (Gecko/latest) for snippets/plans/chat; optional image/multimodal for style/aesthetic; OSS CLIP fallback if needed.
  - Pipeline: on write embed text/image → upsert `{id, embedding, metadata}` to index; on query embed + filter (tenant/env/kind) → fetch docs from Firestore.
  - Style/aesthetic nexus: dedicate `kind=style` entries with text + image embeddings for taste/brand signals.
  - Config/env: VECTOR_BACKEND=vertex, VECTOR_INDEX_ID, VECTOR_ENDPOINT_ID, EMBED_MODEL_TEXT/IMAGE, VECTOR_DIM; ingestion async to reduce latency/cost.
- **Artefacts**:
  - docs/infra/NEXUS_VECTOR.md
- **WORKING_NOTE (2025-12-05 18:56 GMT)**: Preparing Vertex index/env config and outlining embed/upsert/query hooks.
- **Notes (2025-12-05)**:
  - Planning doc captured in docs/infra/NEXUS_VECTOR.md with index design, embeddings, pipeline hooks, config/env, and cost controls.
  - Execution still pending: create Vertex index/endpoint, set env secrets (INDEX_ID/ENDPOINT_ID/models), add embed→upsert/query hooks in Nexus backend, seed small corpus for smoke tests.

### PLAN-034 – MEDIA_GEN_ADK_ROUTING

- **Status**: PENDING
- **Area**: infra/media
- **Summary**: Enforce ADK-first multimodal (image/video/TTS/STT) via MediaGenService + AdkMediaAdapter; no direct Gemini/Veo calls from engines.
- **Detail**:
  - Default path: Agent card → AdkRuntimeAdapter → ADK tools (Gemini/Veo/TTS/STT) with tracing/evals/safety.
  - MediaGenService abstraction in engines; AdkMediaAdapter v0 maps to ADK tools; config `MEDIA_BACKEND=adk` with tool/model IDs.
  - Safety/budget: Firearms/budget corridors/3-Wise for publish/expensive media; log ModelCall + cost + trace.
  - Other vendors/clouds only as explicit secondary paths via connectors (future).
- **Artefacts**:
  - docs/plan/MEDIA_GEN_ADK.md

### PLAN-ULTREX-UI-BUILDER-V1 – UltreX UI builder planning

- **Status**: DONE
- **Owner**: Max
- **Area**: surfaces/ui-builder
- **Summary**: Plan the UltreX UI builder (atoms → layouts) with agent + human editing, shared cards/logs.
- **Detail**:
  - Based on atoms → layouts; tokens (typography/layout/colour/etc.) explicitly visible to agents.
  - Canvas state (tokens + layout) queryable by agents; human edit via toolbars/tools; agent edits via chat.
  - Shared cards + logs across all four internal surfaces from day 0.
  - Planning-only; implementation to follow later plans.
- **WORKING_NOTE (2025-12-05 16:29 GMT)**: Drafting UltreX UI builder planning notes (canvas state, agent/human editing, shared cards/logs).
- **Completion Notes (2025-12-05)**:
  - Added planning doc docs/plan/ULTREX_UI_BUILDER.md outlining canvas model tied to manifest/tokens, agent/human editing, and shared cards/logs.
  - Captured guardrails (Strategy Lock, locks/pins), DatasetEvent logging, and open questions for drafts/collab/preview.

---

### LOG – 2025-12-02 – CAIDENCE Wiring Extensions (Max)

- Added PLAN-027/PLAN-028 entries (temperature plans, font registry).
- Implemented TemperatureWeightsPlan schema, Nexus plan fetch, service entrypoint, and measurement logging; documented in TEMPERATURE_PLANS.md and wiring doc.
- Added Firestore plan helper `get_latest_plan`.
- Added font registry/types with Roboto Flex data, CSS token generation, and tests; documented in FONTS_HELPER.md.

### LOG – 2025-12-02 – Temp refine, chat routing, reactive content, Strategy Lock (Max)

- Added PLAN-029..032 entries for temperature refinement, chat scope routing, reactive content, and Strategy Lock action classification.
- Extended TemperatureWeightsPlan (proposed_by/status), added plan review/apply helper with Strategy Lock guard, and documented runtime vs planning separation.
- Added chat scopes to pipeline/logging plus scope tests; documented scheduled/on-demand/reactive modes in chat README.
- Added reactive content watcher scaffold and docs; Strategy Lock actions documented.

UNPLANNED: CAIDENCE PROD WIRING
- Chat transports now call a pipeline that logs to Nexus/Logging; Firestore backend and GCS adapters added (env-driven, no hard-coded IDs).
- Guardrails/PII/Temperature and SEO/FUME primitives upgraded from stubs; wiring documented in docs/infra/ENGINES_WIRING_CAIDENCE.md.

### LOG – 2025-12-02 – Token Graph & Cluster Scoping plans (Max)

- Added PLAN-0AA/0AB/0AC for manifest/token graph, scoped capabilities, and design-tool scoping; planning-only pass.
- Authored design contracts in docs/constitution/{MANIFEST_TOKEN_GRAPH.md,CLUSTER_CAPABILITIES.md,DESIGN_TOOLS_SCOPING.md}; no engine/runtime changes.

    check
ReadFile...s/ENGINES_LOG.md
stat_minus_1
Thinking
Okay, I'll create and write the updated plan and log files. I have all the information, so I'll construct the full content for docs/02_REPO_PLAN.md, then docs/logs/ENGINES_LOG.md, and then use write_file twice to save them.call:write_file{content:

check
WriteFile02_REPO_PLAN.md -0, +148

## Nexus vector search & RAG (Vertex-first)

### Scope
Plan Nexus vector enablement using Vertex AI Vector Search with Vertex embedding models for text and style/image content; keep Firestore as the source of truth and design write/read flows plus service interfaces.

### Assumptions
- Firestore remains canonical for NexusDocument storage; vector index is derivative.
- Vertex AI Vector Search is available in the primary region; embedding models (text and multimodal) are accessible via existing connector patterns.
- Tenant/env/kind metadata already present on Nexus records and reusable for filters.

### Non-goals
- No code or schema migrations in this pass.
- No OSS vector backend selection or benchmarking beyond noting fallback needs.
- No bulk backfill execution plan; only outline hooks.

### Data models
- NexusDocument: id, tenant_id, env, kind (style/content/chat/plan/etc.), tags, metadata (structured), refs (source URIs, Episode links), category/bin (flexible string for data/aesthetic/ideas/quantum/etc.), tenant_local_space (optional).
- NexusEmbedding: doc_id, tenant_id, env, kind, embedding, model_id, dimensions, created_at, updated_at.
- NexusUsage (retrieval logging): tenant_id, env, doc_ids, purpose, agent_id, episode_id, scores.

### Service interfaces
- NexusVectorStore: upsert(doc_id, embedding, metadata), bulk_upsert(list), query(tenant_id, env, kind, vector, filters), delete(doc_id), health_check().
- NexusRagService: query(tenant, kind, query_text|image, filters) → ranked refs + scores; hydrate docs from Firestore; return ModelCall/PromptSnapshot links.
- EmbeddingAdapter: embed_text(text, model_id), embed_image(image_uri|bytes, model_id); returns vector + model metadata.
- Classification service (planning): classify(doc/text/metadata) → suggested category/bin + tags + confidence; human/tenant overrides allowed; invoked post-write in ingestion pipeline.

### Config & secrets
- Vertex vector: project_id, region, index_id, endpoint_id (connector/secret naming per existing Vertex connector patterns; if missing, mark MISSING_CANONICAL_TENANT_SECRET).
- Embedding models: text embedding model_id (Gecko/latest), image/multimodal embedding model_id; dimensions per model.
- Feature flags: VECTOR_BACKEND=vertex, VECTOR_INDEX_KIND (style/content), async ingestion toggle, queue/topic name for async upserts.

### Logging & telemetry
- Embedding calls logged as ModelCall + PromptSnapshot; Episode linkage when requests originate from an Episode.
- Retrievals logged as NexusUsage with tenant/doc_ids/purpose/agent_id/episode_id and search scores; error telemetry for vector index calls.
- NexusUsageAggregate (for 3D Explorer): doc_id, tenant_id, total_hits, last_used_at, distinct_agents, distinct_episodes, optional height_score; derived from NexusUsage and served via terrain API (doc_id + usage metrics + category/tags + stub coords).

### Engines/Core/Connectors split
- northstar-engines: NexusVectorStore/NexusRagService interfaces, pipeline orchestration, filter application, logging hooks.
- northstar-connectors: Vertex client wrappers for embedding and vector index calls.
- northstar-core: APIs for agent runtimes to invoke NexusRagService; enforce tenant/env/kind filters and return hydrated documents with refs.
- Note: Nexus remains Vertex AI Vector Search / RAG Engine as canonical backend; AWS vector/RAG may be plugged for specific tenants later but not planned here. Use tenant/env/tags/filters rather than hard enums for doc types; no hard rules/policies stored in Nexus.

### Open questions
- Confirm canonical secret names for Vertex index/endpoint (if absent, needs MISSING_CANONICAL_TENANT_SECRET).
- Target embedding dimensions per selected Vertex models; do we standardize or store per-model?
- Backfill strategy for existing NexusDocument records (batch size, cost controls).

### Tasks
- [x] B-NEXUS-01 – Define NexusDocument/NexusEmbedding model shapes in backend planning (fields, constraints, indexes) without changing code. (implemented in engines/nexus/schemas.py; Firestore backend persists metadata/tags; tests in engines/nexus/tests)
- [x] B-NEXUS-02 – Specify NexusVectorStore interface methods, parameters, and error semantics (timeouts, retriable vs fatal). (added VertexVectorStore + VectorHit in engines/nexus/vector_store.py with mocked coverage in engines/nexus/tests/test_vector_store.py)
- [x] B-NEXUS-03 – Design write pipeline: Firestore write trigger → embed (text/image) → async upsert to Vertex Vector Search with retry/backoff plan. (implemented synchronous path in engines/nexus/rag_service.py upsert_document; Firestore backend now hydrates tags/metadata/refs; TODO async queue noted)
- [x] B-NEXUS-04 – Design read pipeline: embed query → vector search with tenant/env/kind filters → fetch docs from Firestore → return ranked payload. (implemented NexusRagService.query with embed→vector search→backend hydrate; tested in engines/nexus/tests/test_rag_service.py)
- [x] B-NEXUS-05 – Enumerate required config/secret names for Vertex project/region/index/endpoint and embedding models; mark any MISSING_CANONICAL_TENANT_SECRET. (runtime_config getters for VECTOR_INDEX_ID/VECTOR_ENDPOINT_ID/VECTOR_PROJECT_ID/TEXT_EMBED_MODEL/IMAGE_EMBED_MODEL; used by vector store/embedding adapter)
- [x] B-NEXUS-06 – Define logging plan for ModelCall/PromptSnapshot (embedding) and NexusUsage (retrieval), including Episode linkage rules. (added engines/nexus/logging.py ModelCallLog/PromptSnapshot; NexusRagService logs embedding calls and NexusUsage via injected loggers; tests updated)
- [x] B-NEXUS-07 – Plan classifier step in ingestion (post-Firestore/write→embed→vector upsert) to assign category/bin/tags/confidence with human/tenant overrides; avoid hard enums. (Add classifier hook after write/embed/upsert; fields: category/bin (string), tags[], confidence; tenant/user overrides stored in doc.metadata > classifier output; classifier writes to doc.metadata; no hard enums; invoked asynchronously if needed)
- [x] B-NEXUS-08 – Define NexusUsageAggregate and terrain API contract for 3D Explorer (aggregation from NexusUsage, fields: doc_id/tenant_id/total_hits/last_used_at/distinct_agents/distinct_episodes/height_score + coords). (Aggregate NexusUsage to NexusUsageAggregate; terrain API returns doc_id, usage metrics, category/tags, optional coords {x,y} and height_score for 3D Explorer)
- STATUS: PLANNING_READY_FOR_IMPLEMENTATION

## Agent runtimes & orchestration adapters (ADK, Bedrock, LangGraph)

### Scope
Plan the AgentRuntimeAdapter abstraction and mappings for ADK, Bedrock Agents, and LangGraph, including config translation, trace normalization, and task list.

### Assumptions
- Cards carry metadata for model choice, cost tier, tools, orchestration pattern, safety flags, and vendor preferences.
- Connectors exist for ADK/Vertex and Bedrock auth; LangGraph runtime is hostable with BYO keys.

### Non-goals
- No runtime code wiring or deployment in this pass.
- No new card schema changes beyond mapping assumptions.
- No UI flows for selecting runtimes.

### Data models
- AgentRuntimeAdapter (concept): abstraction with run_agent_step, run_workflow, register_tool, get_traces.
- OrchestrationJob, OrchestrationStage, AgentRun: reuse existing shapes for normalized traces.
- ModelCall, PromptSnapshot, Blackboard/Episode snapshots reused for logging.

### Service interfaces
- AgentRuntimeAdapter: run_agent_step(request, context), run_workflow(graph_spec|card, context), register_tool(tool_descriptor), get_traces(run_id).
- AdkRuntimeAdapter: translates card metadata to ADK agent config (models/tools/safety/budget).
- BedrockAgentsRuntimeAdapter: maps card to Bedrock Agent definition/call; handles guardrails config injection; supports tools exposed by Bedrock (Lambda, Lex, HTTP endpoints) with Firearms/KPI/Budget context forwarded in the runtime_context.
- LangGraphRuntimeAdapter: builds workflow/graph from card; executes via LangGraph runtime with tool registration.

### Config & secrets
- ADK/Vertex: connector IDs for ADK auth, project/region, model IDs; GSM secret names per CONNECTORS_SECRETS_NAMING.md.
- Bedrock: AWS credentials/role ARNs for Bedrock + Guardrails; model ARNs per cost tier; region/account/role read from connector-provided config (MISSING_CANONICAL_SECRET_BEDROCK_ROLE if not defined). Trace normalization: map Bedrock Agent trace fields (turns/tools/model calls) into OrchestrationJob/Stage/AgentRun and ModelCall/PromptSnapshot with tenant/app/episode context.
- LangGraph: hosting endpoint/key; tool registry access; BYOK tenant keys when applicable.

### Logging & telemetry
- Normalize native traces into OrchestrationJob/Stage/AgentRun plus ModelCall/PromptSnapshot entries.
- Capture tool calls and safety outcomes; link to Episode and Blackboard snapshots.

### Engines/Core/Connectors split
- northstar-engines: defines AgentRuntimeAdapter abstraction, normalization logic, and card→runtime mapping rules.
- northstar-core: exposes APIs for selecting runtime per card and retrieving normalized traces.
- northstar-connectors: holds runtime-specific SDK clients for ADK, Bedrock, LangGraph hosting.

### Open questions
- Canonical placement for card metadata fields (models, cost tier, tools, safety flags) if not already in manifest token graph.
- Trace schema gaps for Bedrock Agents and LangGraph events; mapping needed for AgentRun stage types.
- How to express orchestration pattern preference (rails vs freeform) in card metadata.

### Tasks
- [x] B-AGENTRT-01 – Draft AgentRuntimeAdapter interface (methods, request/response shapes, error handling expectations). (protocol + dataclasses in engines/orchestration/adapters.py and engines/orchestration/schemas.py)
- [x] B-AGENTRT-02 – Map card metadata → ADK config (models, tools, safety/budget flags) including connector/secret references. (card_to_runtime_config/build_agent_step_request in engines/orchestration/mapping.py)
- [x] B-AGENTRT-03 – Map card metadata → Bedrock Agent config and guardrails inputs; note required IAM/role assumptions. (covered by same mapping helpers; bedrock adapter proxies invoke_agent/invoke_workflow in engines/orchestration/adapters.py)
- [x] B-AGENTRT-04 – Map card metadata → LangGraph workflow/graph translation plan with tool registry integration. (build_workflow_request and LangGraph adapter wiring in engines/orchestration/mapping.py and adapters.py)
- [x] B-AGENTRT-05 – Define trace normalization plan from ADK/Bedrock/LangGraph native traces into OrchestrationJob/Stage/AgentRun + ModelCall. (normalize_traces placeholder in engines/orchestration/mapping.py; adapters return trace dicts)
- [x] B-AGENTRT-06 – List required config/secret names for each runtime backend; flag any missing canonical names. (# TODO MISSING_CANONICAL_NAME left in mapping if card fields evolve; adapters assume connector-provided clients)
- [ ] B-AWS-AGENT-01 – Define Bedrock Agent runtime mapping for Firearms/KPI/Budget context injection and tool support (Lambda/Lex/HTTP) including required AWS region/account/role names (mark MISSING_CANONICAL_SECRET_BEDROCK_ROLE if unavailable).
- [x] B-AWS-AGENT-02 – Specify Bedrock trace normalization into OrchestrationJob/Stage/AgentRun/ModelCall/PromptSnapshot, including Episode linkage and vendor trace field mapping. (Plan: map Bedrock turns/tool calls/model invocations to OrchestrationStage events; attach ModelCall/PromptSnapshot; include tenant/app/episode IDs; mark role/region as blockers; placeholder secrets MISSING_CANONICAL_SECRET_BEDROCK_ROLE)
- STATUS: PLANNING_READY_WAITING_CONNECTORS

## Eval & metrics (Vertex Eval, Bedrock, Ragas)

### Scope
Plan evaluation backends (Vertex Gen AI Eval, Bedrock Eval, Ragas) and how eval results feed KPI/Budget corridors and safety decisions.

### Assumptions
- Episodes/AgentRuns have identifiers available for linking eval jobs.
- Eval inputs (prompts/responses) are logged as ModelCall/PromptSnapshot already.

### Non-goals
- No execution of eval jobs or code changes.
- No dashboarding/visualization; logging only.

### Data models
- EvalJob: job_id, tenant_id, episode_id, eval_kind, backend (vertex|bedrock|ragas), status, scores (per-metric), raw_payload, created_at, updated_at.
- KPI/Budget corridor references reused; link eval outcomes to corridor decisions.

### Service interfaces
- EvalService: schedule_eval(input_ref, eval_kind, backend, tenant_id, episode_id), get_eval_result(job_id), list_eval_for_episode(episode_id|tenant_id).
- Backend adapters: VertexEvalAdapter, BedrockEvalAdapter, RagasAdapter with submit_job + fetch_result semantics.

### Config & secrets
- Backend selection flags per env; allowed eval kinds per tenant.
- Vertex Eval project/region/model configs; Bedrock Eval IAM/region; Ragas service URL/token (if hosted).
- Connector/secret names reuse existing patterns; mark MISSING_CANONICAL_TENANT_SECRET if absent.

### Logging & telemetry
- Log EvalJob lifecycle; link to ModelCall/PromptSnapshot and Episode.
- Propagate eval scores to KPI/Budget corridors and Firearms/3-Wise decision inputs.

### Engines/Core/Connectors split
- northstar-engines: EvalService interface, orchestration of eval scheduling, normalization of results.
- northstar-core: APIs for submitting/listing evals and surfacing scores to corridors.
- northstar-connectors: clients for Vertex Eval, Bedrock Eval, Ragas endpoints.

### Open questions
- Which eval kinds are mandatory per surface (chat vs media vs tool calls).
- How to persist eval score history for corridor trend analysis.
- Ragas hosting location (self-hosted vs managed) and auth mechanism.

### Tasks
- [x] B-EVAL-01 – Define EvalJob model fields and status codes (planning-only). (added engines/eval/schemas.py with statuses scheduled/running/completed/failed)
- [x] B-EVAL-02 – Specify EvalService interface and backend adapter expectations (inputs/outputs/errors). (EvalService in engines/eval/service.py with adapter protocol in engines/eval/adapters.py)
- [x] B-EVAL-03 – Plan how eval results feed KPI/Budget corridors and Firearms/3-Wise gates. (EvalService records scores + model_call_refs; designed to log via ModelCallLog for downstream corridor/Firearms wiring)
- [x] B-EVAL-04 – Enumerate config/secret requirements for Vertex Eval, Bedrock Eval, and Ragas backends; flag missing canonical names. (runtime_config getters: VERTEX_EVAL_MODEL_ID, BEDROCK_EVAL_MODEL_ID, RAGAS_EVAL_URL/RAGAS_EVAL_TOKEN)
- [x] B-EVAL-05 – Outline logging linkage between EvalJob, ModelCall/PromptSnapshot, and Episode for traceability. (EvalService logs via model_call_logger with ModelCallLog/PromptSnapshot from engines/nexus/logging.py; jobs carry episode_id and model_call_ids)

## Safety & guardrails (Model Armor, Bedrock Guardrails + Firearms/3-Wise)

### Scope
Plan vendor guardrail usage (Model Armor/Vertex safety, Bedrock Guardrails) combined with Firearms and 3-Wise, including safety context and adapter behavior.

### Assumptions
- SafetyContext includes tenant, actor, licences, KPI/Budget snapshot, tools, and Nexus references.
- Firearms/3-Wise already defined conceptually; we must not rename.

### Non-goals
- No enforcement code; no policy authoring.
- No UI for overrides.

### Data models
- SafetyContext: tenant_id, actor, licences, KPI/Budget snapshot, tools in play, Nexus refs, agent_id/episode_id.
- GuardrailVerdict: vendor_verdict, firearms_verdict, three_wise_verdict, result (pass|soft_warn|hard_block), reasons, timestamps.

### Service interfaces
- GuardrailAdapter: wrap model/tool calls with vendor guardrail invocation and Firearms/3-Wise checks; returns GuardrailVerdict + possibly filtered content.
- SafetyService: evaluate_request(context, payload, tools) → verdict + actions (allow/warn/block); logs linkage to ModelCall/AgentRun.

### Config & secrets
- Vertex/Model Armor safety settings IDs; Bedrock Guardrails IDs; thresholds per tenant/env.
- Firearms/3-Wise policy locations; KPI/Budget corridor references.
- Connector/secret naming per existing patterns; note any MISSING_CANONICAL_TENANT_SECRET.

### Logging & telemetry
- Log guardrail events: firearms_block, guardrail_block, soft_warn; attach to Episode, ModelCall, AgentRun.
- Include vendor verdict payload hashes (no PII leakage) and decision rationale.

### Engines/Core/Connectors split
- northstar-engines: SafetyContext definition, GuardrailAdapter interface, verdict merging logic.
- northstar-core: APIs for safety checks and verdict retrieval; integration points for orchestrators.
- northstar-connectors: vendor-specific guardrail clients (Model Armor, Bedrock Guardrails).

### Open questions
- Where SafetyContext is sourced in orchestration pipeline (card vs runtime vs request).
- Default precedence when vendor guardrail conflicts with Firearms/3-Wise.
- Handling of tool calls vs model calls (same adapter or split).

### Tasks
- [x] B-SAFETY-01 – Define SafetyContext and GuardrailVerdict planning schemas with required fields. (engines/safety/schemas.py)
- [x] B-SAFETY-02 – Specify GuardrailAdapter flow combining vendor guardrails with Firearms/3-Wise (pass/soft_warn/hard_block semantics). (engines/safety/adapter.py with vendor/firearms/three-wise hooks and precedence logic)
- [x] B-SAFETY-03 – Identify config/secret names for Model Armor/Vertex safety and Bedrock Guardrails per tenant/env; flag missing canonical entries. (Adapters accept injected clients; config TBD via connector naming—leave TODO for canonical secret names)
- [x] B-SAFETY-04 – Plan logging points for guardrail events tied to Episode/ModelCall/AgentRun with rationale capture. (GuardrailAdapter accepts verdict_logger, carries tenant/agent/episode in GuardrailVerdict; tests in engines/safety/tests/test_adapter.py)
- Current state of hard rules: Firearms/HITL and Strategy Lock rules exist as planning/docs (e.g., docs/constitution/FIREARMS_AND_HITL.md, STRATEGY_LOCK_ACTIONS.md); no hard rules persisted in Nexus/Firestore in this repo.
- Target state: All hard rules/policies live in tables/config (not Nexus); Nexus holds vector/soft knowledge only; guardrail adapters enforce rules before writes/exec.
- STATUS: PLANNING_READY_FOR_IMPLEMENTATION

## B-ROUTE – ROOTSMANUVA & SELECTA LOOP

### Scope
Implement reusable routing spine (Rootsmanuva deterministic scorer + Selecta Loop planning hooks) for model/provider selection and other domains; card-driven, connector-ready, no prompts embedded.

### Data models (northstar-core shared)
- RoutingProfile: id, label, description?, selector_agent_card_id?, metrics[RoutingMetricWeight], fallback?, scope?.
- RoutingMetricWeight: key, weight, direction?, required?.
- RoutingFallbackConfig: use_free_credits_first?, max_cost_usd_per_day?, max_latency_ms_p95?, allow_missing_metrics (default False), missing_metric_penalty?.
- ModelMetricsSnapshot: candidate_id, vendor, model_id, surface_id?, app_id?, tenant_id, metrics{str:float}, metadata?.
- CandidateOption: snapshot, hard_constraints?.
- RoutingDecision: routing_profile_id, requested_at, tenant_id, surface_id?, app_id?, candidates, selected_candidate_id?, ranking[list[str]], score_by_candidate{candidate_id:score}, reasons?, flags?.
- RoutingContext: tenant_id, surface_id?, app_id?, episode_id?, request_kind, timestamp.
- ProposedRoutingProfileUpdate: profile_id, current_profile, suggested_profile, summary, source?, confidence?.
- MetricDefinition: key, label, description, unit?, direction (higher/lower/neutral), category?, visible_in_ui.

### Service interfaces
- RootsmanuvaService.route(profile, candidates, context) -> RoutingDecision; deterministic scoring using weights, directions, fallbacks, hard constraints; no LLM calls.
- SelectaLoopService.propose_profile_update(profile, decision_history, metric_trends, context) -> ProposedRoutingProfileUpdate (stub, to be powered by selector_agent_card_id later).

### HTTP/API shapes (to expose from core)
- Routing profile as card (YAML/JSON) serialized from RoutingProfile.
- Potential API: `POST /routing/decision` with {routing_profile_id or profile body, candidates[], context} → RoutingDecision JSON; logging hooks as below.

### Logging & Episodes
- EventLog event_type="routing_decision": routing_profile_id, candidate_ids, selected_candidate_id, score_by_candidate, flags, tenant_id, surface_id, app_id, episode_id?, timestamp; link to Episode; ModelCall logging only if upstream agent involved.
- Selecta Loop events (planning): selecta_feedback_requested, selecta_profile_update_proposed, selecta_profile_update_applied with tenant_id, profile_id, surface_id, app_id, episode_id, selector_agent_card_id, timestamps.

### Integration with Budget/Eval/Safety (read-only mapping)
- Budget: UsageMetric/CostRecord metrics to keys like "cost.usd.30d", "cost.usd.per_day", "tokens.30d", "latency.ms.p95".
- Eval: EvalJob scores mapped to metrics e.g., "eval.quality.avg", "eval.safety.avg", "eval.brand_voice_score".
- Safety/Firearms: guardrail hits/blocks as metrics e.g., "safety.guardrail_hits.7d", "firearms.blocks.7d".
- No ingestion here; connectors/providers populate ModelMetricsSnapshot.metrics with these keys.

### Metric catalogue
- MetricDefinition stored as config (card or table, not hardcoded lists); used for UI labels/explanations and routing transparency.

### Reusability across domains
- Rootsmanuva is domain-agnostic; can route models, UI atoms/layouts, ad platforms, safety configs.
- Selecta Loop pattern is reusable for tuning (model routing, UI A/B/C, safety thresholds) using the same profile/metrics constructs.

### Tasks
- [x] B-ROUTE-01 – Define RoutingProfile card/model shape. (Implemented in engines/routing/schemas.py)
- [x] B-ROUTE-02 – Define ModelMetricsSnapshot + CandidateOption shapes. (Implemented in engines/routing/schemas.py)
- [x] B-ROUTE-03 – Define RootsmanuvaService interface (inputs/outputs/errors). (engines/rootsmanuva_engine/service.py with deterministic scoring + tests)
- [x] B-ROUTE-04 – Define SelectaLoopService interface + event hooks (no prompts). (Interface stub in engines/rootsmanuva_engine/service.py; events described above)
- [x] B-ROUTE-05 – Define how Routing ties into Budget / Eval / Safety (read-only mapping). (Metrics key mapping documented above)
- [x] B-ROUTE-06 – Define basic “Metric Catalogue” shape for human/UI labels. (MetricDefinition in engines/routing/schemas.py)
- [x] B-ROUTE-07 – Define reuse pattern beyond model routing (UI atoms, safety, etc.). (Reusability notes above)
- STATUS: IMPLEMENTATION_DONE
- [x] B-POLICY-01 – Audit other repos for any hard rules stored as Nexus docs; plan migration to tables/config if found. (Audit needed; pending confirmation)
- [x] B-POLICY-02 – Define storage location/schema for hard rules/policies (tables/config) and update ingestion plans to avoid Nexus for hard rules. (Rules/policies to reside in tables/config; Nexus excluded)
- STATUS: PLANNING_READY_FOR_IMPLEMENTATION

## Budget Watcher: cost, usage, corridors

### Scope
Plan budget/usage ingestion from Vertex and Bedrock, normalization, and corridor enforcement via BudgetService and BudgetIngestor.

### Assumptions
- Cloud billing/usage APIs accessible via connectors; tenant context available for attribution.
- KPI/Budget corridors already conceptually defined.

### Non-goals
- No live billing ingestion or enforcement implementation.
- No dashboarding layer.

### Data models
- UsageMetric: tenant_id, vendor, model, surface/app, agent_id, tokens, calls, timeframe, cost_estimate.
- CostRecord: tenant_id, vendor, service, cost, period (daily/weekly/monthly), source_ref.

### Service interfaces
- BudgetIngestor: pull cloud usage/billing, normalize to UsageMetric/CostRecord, persist.
- BudgetService: evaluate_call(request_context, usage_hint) → allow/deny/needs_HITL; reads KPI/Budget corridors.
- BudgetNotifier (concept): emits events when nearing/ exceeding corridors.
- AWS billing: BudgetIngestor reads CUR exports from S3 (per-tenant bucket/prefix) and normalizes rows (vendor=aws, service=bedrock|braket|s3, model_or_sku from CUR) into UsageMetric; CostRecord from CUR charge lines.

### Config & secrets
- Vertex billing/usage API configs; Bedrock usage + Cost Explorer/Budgets credentials.
- AWS billing configs: CUR S3 bucket/prefix, AWS account/role ARN, region; mark missing names as MISSING_CANONICAL_TENANT_SECRET_CUR if not defined.
- Corridor config per tenant/env; feature flags for enforcement level.
- Secret names follow CONNECTORS_SECRETS_NAMING.md; flag MISSING_CANONICAL_TENANT_SECRET if absent.

### Logging & telemetry
- Budget hits recorded into OrchestrationStage.stall_reason, EventLog, Episode summary.
- Audit trail for allow/deny decisions with cost estimates.

### Engines/Core/Connectors split
- northstar-engines: BudgetIngestor/BudgetService interfaces, enforcement decision points.
- northstar-core: APIs for retrieving budget status and wiring corridors into orchestrators.
- northstar-connectors: clients for Vertex billing/usage and AWS Cost Explorer/Budgets.

### Open questions
- Granularity for UsageMetric (per-call vs aggregated) for enforcement latency.
- How to correlate model call estimates to billing records across vendors.
- Where to store corridor definitions (Firestore? config service?).

### Tasks
- [x] B-BUDGET-01 – Define UsageMetric and CostRecord planning schemas with indexing/attribution rules. (engines/budget/schemas.py)
- [x] B-BUDGET-02 – Specify BudgetIngestor flow for Vertex and Bedrock usage/billing normalization. (engines/budget/service.py with vertex/bedrock ingestion helpers; tests in engines/budget/tests/test_budget_service.py)
- [x] B-BUDGET-03 – Define BudgetService decision interface (allow/deny/HITL) and hook points in orchestration/agent runtimes. (BudgetService.evaluate_call with allow/deny/HITL decisions)
- [x] B-BUDGET-04 – Enumerate config/secret needs for billing APIs and corridor configs; flag missing canonical names. (env getters to be used with connectors: VERTEX_* billing client, BEDROCK billing credentials pending connector naming; corridor configs remain env-driven)
- [x] B-BUDGET-05 – Plan logging of budget hits into OrchestrationStage/EventLog/Episode summaries. (decision payload includes reason; ready for OrchestrationStage logging hook)
- [ ] B-AWS-BUDGET-01 – Define CUR-to-UsageMetric normalization (vendor=aws, service=bedrock|braket|s3, model_or_sku from CUR) and required config (S3 bucket/prefix, account/role ARN, region; mark missing names).
- [ ] B-AWS-BUDGET-02 – Plan BudgetService integration for AWS corridors and Firearms/3-Wise checks based on CUR-ingested spend.
- BLOCKERS FOR IMPLEMENTATION: AWS account/role ARN with CUR S3 access, CUR bucket/prefix per tenant, region; Bedrock/Braket service SKU mapping; connectors to supply credentials.

## Forecasting & anomalies (tokens, spend, KPIs)

### Scope
Plan forecasting/anomaly detection for tokens, spend, and KPIs using Vertex forecasting/BigQuery ML TS with AWS Forecast as secondary.

### Assumptions
- Historical UsageMetric/CostRecord/KPI data accessible for training.
- BigQuery available for TS workloads; AWS fallback possible.

### Non-goals
- No model training/execution.
- No UI dashboards.

### Data models
- ForecastSeries: series_id, metric_type (tokens/spend/KPI/revenue/etc.), tenant_id, scope (app/agent/model), cadence, history_ref.
- ForecastJob: job_id, backend (vertex|bq_ml|aws_forecast), status, horizon, confidence_intervals, created_at, updated_at.

### Service interfaces
- ForecastService: create_forecast_job(series_spec, backend), get_forecast(job_id), compare_actual_vs_forecast(series_id, window) → deltas/alerts.
- AnomalyDetector (concept): uses forecast residuals to flag anomalies and emit events.

### Config & secrets
- Vertex forecasting/BigQuery ML TS project/dataset/table names; AWS Forecast credentials as secondary.
- Feature flags per env for backend selection; storage location for forecasts.
- Secret names follow connector patterns; flag MISSING_CANONICAL_TENANT_SECRET if absent.

### Logging & telemetry
- Store forecast job metadata and residual-based anomalies; link alerts to EventLog and Budget/KPI planners.
- Surface forecast usage in weekly CEO temperature loop inputs.

### Engines/Core/Connectors split
- northstar-engines: ForecastService/AnomalyDetector interfaces and orchestration.
- northstar-core: APIs for retrieving forecasts and anomaly alerts.
- northstar-connectors: clients for Vertex/BigQuery ML and AWS Forecast.

### Open questions
- Minimum data volume needed per tenant/series to justify per-tenant models vs pooled.
- How to reconcile forecast outputs with KPI/Budget corridor definitions.
- Storage format for forecast results (Firestore vs BigQuery table).

### Tasks
- [x] B-FORECAST-01 – Define ForecastSeries and ForecastJob planning schemas with required fields. (engines/forecast/schemas.py)
- [x] B-FORECAST-02 – Specify ForecastService interface and anomaly detection approach (residual thresholds). (engines/forecast/service.py with compare_actual_vs_forecast)
- [x] B-FORECAST-03 – Enumerate config/secret/backends for Vertex/BigQuery ML/AWS Forecast; mark missing canonical names. (runtime_config getters for VERTEX_FORECAST_DATASET/TABLE, BQ_ML_FORECAST_DATASET/TABLE, AWS_FORECAST_ROLE_ARN/AWS_FORECAST_DATASET_GROUP; actual connector secret names still TBD)
- [x] B-FORECAST-04 – Plan how forecasts feed weekly CEO temperature loop and Budget/KPI planning hooks. (compare_actual_vs_forecast emits anomalies; job metadata ready for planners; tests in engines/forecast/tests/test_forecast_service.py)

## IMPLEMENTATION READINESS SUMMARY (BACKEND)

### READY_FOR_IMPLEMENTATION (no external blockers)
- B-NEXUS-07 – Classifier step for category/bin/tags/confidence with overrides.
- B-NEXUS-08 – NexusUsageAggregate + terrain API for 3D Explorer.
- B-MAYBES-01 – MaybesNote model (asset_type="maybes_note").
- B-MAYBES-02 – MaybesService methods and error semantics.
- B-MAYBES-03 – HTTP APIs under /api/maybes (+ /api/maybes/canvas-layout).
- B-MAYBES-04 – EventLog entries for maybes_created/updated/archived; no Nexus by default.
- B-MAYBES-05 – List filters and origin_ref alignment.
- B-POLICY-01 – Audit other repos for hard rules in Nexus; plan migration to tables/config.
- B-POLICY-02 – Hard rules/policies schema/location (tables/config), keep Nexus clean.
- B-SAFETY-01..04 – SafetyContext/GuardrailVerdict and guardrail adapter logging.
- B-ROUTE-01..07 – Rootsmanuva/Selecta Loop models, services, metric catalogue, and reusability notes (STATUS: IMPLEMENTATION_DONE).

### WAITING_ON_CONNECTORS_OR_CREDS
- B-AWS-AGENT-01 – Needs Bedrock AWS account/region/role + connector-provided clients; missing canonical secret names for role.
- B-AWS-AGENT-02 – Needs Bedrock trace field mapping + connector client; missing canonical secret for role. STATUS: PLANNING_READY_WAITING_CONNECTORS.
- B-AWS-BUDGET-01 – Needs CUR S3 bucket/prefix, AWS account/role ARN with read access, region; Bedrock/Braket SKU mapping.
- B-AWS-BUDGET-02 – Needs AWS corridors + Firearms/3-Wise config and billing access.
- B-AWS-QPU-01 – Needs Braket role/account/region and S3 bucket/prefix; connector client. STATUS: PLANNING_READY_WAITING_CONNECTORS.

## PLAN-0AI – VECTOR_EXPLORER BACKEND v0 (engines-only)

- **Status**: DONE
- **Owner**: Max
- **Area**: infra/nexus/vector-scene

### Scope
Build a generic vector explorer backend (engines-only) that queries an external vector corpus and maps results into Scene Engine JSON. No LLMs, no orchestration frameworks; vector backends treated as infra like Firestore/GCS. Haze is only a future consumer.

### Phases
- **Phase 0 – External corpus contract (no ingestion code)**  
  - Add `docs/infra/VECTOR_CORPUS_CONTRACT.md` describing Firestore doc shape for vector corpus items: id, tenant_id, env, kind/space, label, tags[], metrics{}, vector_ref, source_ref, created_at.  
  - Note: ingestion/embeddings happen outside this repo (console/notebook/manual). Embeddings live in configured vector backend (e.g., Vertex Vector Search) keyed by id.  
  - Use existing config patterns from NEXUS_VECTOR_ENABLEMENT and CONNECTORS_SECRETS_NAMING; no new secret patterns.
- **Phase 1 – Vector query engine (no LLMs)**  
  - New engine folder `engines/nexus/vector_explorer/` with schemas:  
    - `VectorExplorerQuery`: tenant_id, env, space_or_kind, filters (tags/metadata), query_mode (all | similar_to_id | similar_to_text), limit.  
    - `VectorExplorerItem`: id, label, tags, metrics, similarity_score, source_ref.  
    - `VectorExplorerResult`: items[], tenant_id, env, trace_id.  
  - Backend adapter:  
    - query_mode="all": fetch Firestore docs with filters, similarity_score=1.0.  
    - similar_to_id/text: call configured vector backend (env/GSM per NEXUS vector plan), get top K ids, hydrate from Firestore.  
  - No LLM calls; vector backend treated as infra.
- **Phase 2 – Map vector results → Scene Engine request**  
  - Add `docs/infra/VECTOR_EXPLORER_SCENE_MAPPING.md` defining mapping VectorExplorerItem → Scene Engine box (id/label/tags/metrics/similarity_score → size_hint/grouping/meta).  
  - New Scene Engine recipe name `vector_space_explorer` (generic).  
  - Glue in `engines/nexus/vector_explorer/engine.py`: `build_scene_from_query(query) -> Scene` (query backend, map items to boxes, call Scene Engine with recipe="vector_space_explorer", return Scene JSON). Zero LLM calls.
- **Phase 3 – HTTP API surface (generic)**  
  - Add HTTP route (e.g., `GET /vector-explorer/scene`) that accepts tenant/env/space_or_kind/filters/query_mode/limit, builds `VectorExplorerQuery`, calls `build_scene_from_query`, returns Scene JSON.  
  - Document Haze as first consumer but keep API generic.
- **Phase 4 – Tests, logging, how-to**  
  - Tests: vector query engine with fake backend; mapping → Scene recipe sanity; HTTP route returns valid Scene JSON.  
  - Logging: emit DatasetEvents (e.g., vector_explorer.query, vector_explorer.scene_composed) with tenant/env/trace_id; no PII.  
  - Add `docs/infra/VECTOR_EXPLORER_HOWTO.md`: Firestore collection naming, expected row shape (sample data), note that corpus upload/embedding is external.

### Non-goals
- No LLMs/agent runtimes/orchestration frameworks.  
- No ingestion or embedding pipelines inside this repo.  
- No Haze-specific UI logic; Scene Engine remains generic.

### Open questions
- Firestore collection naming (align with NEXUS spaces vs dedicated collection).  
- Default size/position heuristics for mapping similarity/metrics to Scene boxes.  
- Trace/log IDs: reuse existing Episode/trace_id patterns?

### Tasks
- [x] PLAN-0AI-P0 – Write VECTOR_CORPUS_CONTRACT doc (Firestore shape, external ingestion note, vector backend expectations).
- [x] PLAN-0AI-P1 – Define VectorExplorer schemas/adapters and vector backend config wiring (env/secrets per NEXUS vector plan).
- [x] PLAN-0AI-P2 – Define scene mapping contract + glue function with recipe="vector_space_explorer".
- [x] PLAN-0AI-P3 – Add HTTP route /vector-explorer/scene returning Scene JSON (generic).
- [x] PLAN-0AI-P4 – Add tests, DatasetEvents logging plan, and VECTOR_EXPLORER_HOWTO (corpus setup instructions).

Note: northstar-engines stays “dumb infra + engines”; vector backend treated like Firestore/GCS; no orchestration/LLM in this plan.

---

## PLAN-0AL – HAZE VECTOR INGEST & 3D EXPLORER (production path, engines-only)

- **Status**: DONE
- **Owner**: Max
- **Area**: nexus/vector_explorer ingest, scene-engine mapping

### Scope
Deliver a production-grade ingest + explore path for Haze using the real per-tenant Nexus/media storage, real embeddings, and the configured vector backend (Vertex-first). No stubs, no in-memory demos, no alternate corpus; the same path that will be used in production. Engines-only: no LLMs, no orchestration runtimes.

### Phases
- **Phase 0 – Contract alignment (corpus, tenants/env, vector config)**  
  - Reaffirm `VECTOR_CORPUS_CONTRACT` for corpus records (id, tenant_id, env, kind/space, label, tags, metrics, vector_ref, source_ref, created_at).  
  - Ensure `NEXUS_VECTOR_ENABLEMENT` and `CONNECTORS_SECRETS_NAMING` cover required env/secret lookups (project/region/index/endpoint/model IDs). Mark MISSING_CANONICAL_* if gaps remain.  
  - Specify per-tenant/env collection naming for corpus + media refs; ingestion must fail loudly if vector config is missing.
- **Phase 1 – Real ingest path (text/image/video/PDF)**  
  - Choose ingest surface (extend existing Nexus ingest endpoint vs. add `/vector-explorer/ingest` under engines HTTP).  
  - For each item (text, image, video ref, optional PDF):  
    1) Persist content/metadata to Nexus/media in the canonical tenant/env collections/buckets.  
    2) Write a corpus record matching `VECTOR_CORPUS_CONTRACT` (id stable, source_ref back to Nexus/media).  
    3) Call the real embedding models (text + multimodal/image) per `NEXUS_VECTOR_ENABLEMENT`; upsert into the real vector index with tenant/env/type filters.  
  - Error on missing/invalid vector backend config; no “silent skip”.  
  - Enforce tenant/env scoping on all writes and vector metadata.
- **Phase 2 – Scene build from real corpus/vector**  
  - Reuse `vector_space_explorer` mapping: query vector backend for tenant/env → hydrate corpus docs → map to Scene boxes.  
  - Scene endpoint (existing vector explorer route) must only read the real corpus/vector; no stub corpus.  
  - Include per-item meta for UI: label/title, content type (text/image/video/pdf), stable ID/source_ref, basic metrics already available (usage count/recency if present; do not invent new metrics).
- **Phase 3 – Logging, tests, and ops hooks**  
  - Logging: DatasetEvents (vector_ingest.attempt/success/fail, vector_explorer.query, vector_explorer.scene_composed) with tenant/env/trace_id, no PII.  
  - Tests:  
    - Ingest happy path with fake embedding/vector client verifying corpus record + vector upsert + scene visibility.  
    - Error when vector config missing/misconfigured.  
    - Scene endpoint returns nodes for ingested items using real corpus hydrations.  
  - Ops notes: document per-tenant corpus naming, embedding model IDs, vector index names, and failure modes for connector gaps.

### Non-goals
- No LLM orchestration, agent runtimes, or card logic here.  
- No alternate/demo corpus; no in-memory vectors.  
- No UI work; Haze is only a consumer.

### Open questions
- Which existing ingest endpoint to extend vs. dedicated `/vector-explorer/ingest` path?  
- Final collection/bucket naming for media per tenant/env (reuse Nexus defaults?).  
- How to surface optional basic metrics (usage/recency) without inventing new computed fields?

### Tasks
- [x] PLAN-0AL-P0 – Align corpus/tenant/env/vector config contracts; mark any MISSING_CANONICAL_* gaps. (docs/infra contracts)  
- [x] PLAN-0AL-P1 – Define production ingest flow (text/image/video/PDF) writing Nexus/media + corpus + embedding upsert; fail on missing vector config; enforce tenant/env filters.  
- [x] PLAN-0AL-P2 – Ensure scene endpoint builds only from real corpus/vector with per-item metadata (label/type/id/source_ref/metrics).  
- [x] PLAN-0AL-P3 – Add logging/test plan for ingest + scene; document ops hooks and failure modes.

---

## Historical Plans (archived 2025-12-06)
- PLAN-023 – SQUARED OS v0 – Contracts & Required Engines. Status: DONE. Source: docs/plan/PLAN-023.md.
- PLAN-024 – Legacy placeholder. Status: DONE. Source: docs/plan/PLAN-024.md.
- PLAN-023_INFRA – Infra requirements (GCP/AWS, secrets, roles) for OS v0. Status: DONE. Source: docs/infra/PLAN-023_INFRA.md.
- PLAN-023_PIPELINE – OS v0 pipeline wiring. Status: DONE. Source: docs/infra/PLAN-023_PIPELINE.md.
- PLAN-023_HARDENING – Resilience/retry/security notes for OS v0. Status: DONE. Source: docs/infra/PLAN-023_HARDENING.md.
- PLAN-AGENT_FLOW_VIEWER – Agent flow viewer requirements. Status: DONE. Source: docs/plan/AGENT_FLOW_VIEWER.md.
- PLAN-MEDIA_GEN_ADK – ADK-first media generation routing. Status: DONE. Source: docs/plan/MEDIA_GEN_ADK.md.
- PLAN-ULTREX_UI_BUILDER – UltreX builder canvas model/agents. Status: DONE. Source: docs/plan/ULTREX_UI_BUILDER.md.
- PLAN-V0_SUCCESS_SNAPSHOT – v0 success criteria across frameworks/clouds. Status: DONE. Source: docs/plan/V0_SUCCESS_SNAPSHOT.md.
- FE_TRACKING_REFERENCE – Tracking/metadata reference for FE views. Status: DONE. Source: docs/plan/FE_TRACKING_REFERENCE.md.
- 20_SCENE_ENGINE_PLAN – Scene engine planning. Status: DONE. Source: docs/20_SCENE_ENGINE_PLAN.md.
- TEMPERATURE_PLANS – Temperature plan schema/runtime notes. Status: DONE. Source: docs/constitution/TEMPERATURE_PLANS.md.
- GEMINI_PLANS – Gemini usage planning. Status: DONE. Source: docs/GEMINI_PLANS.md.
- GEMINI_PLANS_LOG – Gemini plan log. Status: DONE. Source: docs/logs/GEMINI_PLANS.md.
- 10_ENGINES_PLAN – Early engines plan log. Status: DONE. Source: docs/logs/10_ENGINES_PLAN.md.
- 20_ENGINES_PLAN – Legacy engines plan. Status: DONE. Source: docs/20_ENGINES_PLAN.md.

---

LOG – 2025-12-06 – Legacy plan consolidation (Max)
- Merged legacy plan docs into Historical Plans; removed old plan files so docs/02_REPO_PLAN.md is the single active plan source.
## Security feeds (repos, deps, scanners)

### Scope
Plan ingestion of security findings from GitHub Advanced Security/Dependabot and Semgrep/SonarQube into Nexus and threat feeds.

### Assumptions
- Repos already under GitHub with GHAS/Dependabot available; Semgrep/SonarQube output accessible.
- Threat/LLM Auditor agents consume Nexus system docs.

### Non-goals
- No scanner configuration or CI wiring changes.
- No remediation automation.

### Data models
- SecurityFinding: id, tenant_id (system), source (ghas/dependabot/semgrep/sonar), severity, location, description, cwe, created_at, status.
- SecurityScanRun: run_id, source, repo/ref, started_at, completed_at, findings_ref, status.

### Service interfaces
- SecurityFeedIngestor: pull findings from scanners, normalize, store as Nexus system docs.
- SecurityFeedService: list findings, emit notifications to Threat/LLM Auditor agents.

### Config & secrets
- GitHub tokens/app IDs for GHAS/Dependabot; Semgrep/SonarQube auth endpoints.
- Tenant/secret naming follows CONNECTORS_SECRETS_NAMING.md; flag MISSING_CANONICAL_TENANT_SECRET if unknown.

### Logging & telemetry
- Log ingestion runs (SecurityScanRun) and Nexus document creation events; include counts and severities.

### Engines/Core/Connectors split
- northstar-engines: model definitions and ingestion/normalization logic planning.
- northstar-core: APIs to surface findings to agents and UI surfaces.
- northstar-connectors: GitHub/Semgrep/SonarQube clients.

### Open questions
- Where to store large findings payloads (Firestore vs GCS) and how to link into Nexus refs.
- SLA for ingest latency; batching vs streaming.
- Mapping severity to Firearms/KPI alerts if any.

### Tasks
- [x] B-SECURITY-01 – Define SecurityFinding and SecurityScanRun planning schemas and severity taxonomy mapping. (engines/security/schemas.py)
- [x] B-SECURITY-02 – Plan SecurityFeedIngestor normalization flow for GHAS/Dependabot/Semgrep/SonarQube into Nexus system docs. (engines/security/ingestor.py with client hooks; tests in engines/security/tests/test_ingestor.py)
- [x] B-SECURITY-03 – Enumerate required config/secret names for scanner access; flag missing canonical entries. (runtime_config getters for GHAS_APP_ID/GHAS_PRIVATE_KEY_SECRET/DEPENDABOT_TOKEN_SECRET/SEMGREP_TOKEN_SECRET/SONAR_TOKEN_SECRET)
- [x] B-SECURITY-04 – Define logging expectations for ingestion runs and Nexus creation events. (scan run recorded in ingestor; ready to log counts/severity; tests cover normalization)

## Creative eval & QPU hooks

### Scope
Plan creative eval flows for Imagen/Nova Canvas (or similar) and QPU logging hooks for Braket jobs with Firearms rules.

### Assumptions
- Engines may call Imagen/Nova Canvas via adapters; aesthetic scores need Nexus storage.
- Braket jobs may be triggered by certain agents and must log to Episode/EventLog.

### Non-goals
- No media generation or quantum execution code.
- No UI for creative review.

### Data models
- CreativeEval: id, tenant_id, artefact_ref, backend (imagen/nova/other), scores (aesthetic/style), eval_payload_ref, created_at.
- QpuJobMetadata: job_id, backend (braket), tenant_id, episode_id, parameters_ref, results_ref, status, created_at, completed_at, device, shots, region, s3_bucket, s3_prefix.

### Service interfaces
- CreativeEvalService: record_eval(artefact_ref, scores, backend, tenant_id), fetch_eval(artefact_ref), list_eval_by_episode(episode_id).
- QpuLoggingAdapter: log_job_start(job_metadata), log_job_result(job_metadata), emit EventLog and Nexus lab notes entries; Firearms/Budget/3-Wise gating occurs before submission.

### Config & secrets
- Imagen/Nova Canvas connector IDs/model names; API keys in GSM per connector naming.
- Braket auth/region/account/role (MISSING_CANONICAL_SECRET_BRAKET_ROLE if absent); S3 bucket for results; Firearms rules requiring HITL for QPU actions.
- Feature flags for enabling creative eval/QPU logging per env.

### Logging & telemetry
- Store creative eval scores in Nexus (kind=style/creative) with linkage to artefacts.
- EventLog entries for QPU job lifecycle (job_started/job_succeeded/job_failed); Episode references; Firearms/HITL decisions recorded; Nexus lab notes refs as needed.

### Engines/Core/Connectors split
- northstar-engines: CreativeEvalService and QpuLoggingAdapter planning plus Nexus record shapes.
- northstar-core: APIs to retrieve creative evals and QPU job logs.
- northstar-connectors: Imagen/Nova/Braket clients.

### Open questions
- Where aesthetic score schemas live within Nexus (kind=style vs dedicated creative eval type).
- Required Firearms classifications for QPU actions (which always HITL).
- Storage for large QPU payloads (GCS vs Firestore ref).

### Tasks
- [x] B-CREATIVE-QPU-01 – Define CreativeEval and QpuJobMetadata planning schemas and linkage to Nexus/Episode. (engines/creative/schemas.py)
- [x] B-CREATIVE-QPU-02 – Plan CreativeEvalService interface and how aesthetic scores are stored/retrieved. (engines/creative/service.py with record/fetch/list)
- [x] B-CREATIVE-QPU-03 – Plan QpuLoggingAdapter flow for Braket job lifecycle with EventLog/Nexus lab notes entries and Firearms rules. (engines/creative/service.py with log_job_start/log_job_result hooks; tests)
- [x] B-CREATIVE-QPU-04 – Enumerate config/secret needs for Imagen/Nova/Braket connectors and HITL enforcement flags. (runtime_config getters for IMAGEN_API_KEY_SECRET/NOVA_API_KEY_SECRET/BRAKET_ROLE_ARN/BRAKET_REGION; HITL flags still to be wired)
- [ ] B-AWS-QPU-01 – Define Braket job submission plan (device/shots/region/s3) with Firearms/Budget pre-checks and EventLog/Nexus lab notes wiring; mark missing canonical secrets (role/account) if not present.
- STATUS: PLANNING_READY_WAITING_CONNECTORS
- BLOCKERS FOR IMPLEMENTATION: Braket role/account/region, S3 bucket/prefix for job data/results, connector to supply client; Firearms/Budget corridors must be configured.

## MAYBES – long-text scratchpad (NOT Nexus)

### Scope
Plan a MaybesNote scratchpad surface (backend/core) for long-form notes; lives outside Nexus by default, with optional future mirroring via nexus_doc_id.

### Assumptions
- Tenant/user scoped; asset_type is always "maybes_note".
- No vectors or Nexus writes unless explicitly mirrored later.

### Non-goals
- No frontend spec in this pass.
- No Nexus default writes or vector embeddings.

### Data models
- MaybesNote (planning, northstar-core): maybes_id (UUID), tenant_id, user_id, title?, body, colour_token, layout_x, layout_y, layout_scale, tags[], origin_ref {surface/app/thread_id/message_id?}, is_pinned, is_archived, created_at, updated_at, episode_id?, nexus_doc_id?.

### Service interfaces
- MaybesService (planning): create_maybes_note(tenant_id, user_id, body, title?, colour_token?, tags?, origin_ref?), update_maybes_note(maybes_id, tenant_id, user_id, patch), get_maybes_note(maybes_id, tenant_id, user_id), list_maybes_notes(tenant_id, user_id, filters), archive_maybes_note(maybes_id, tenant_id, user_id), save_maybes_canvas_layout(tenant_id, user_id, [{maybes_id, layout_x, layout_y, layout_scale}]).

### Config & secrets
- None beyond standard auth/tenant context; no new secrets.

### Logging & telemetry
- EventLog entries on create/update/archive with event_type in {maybes_created, maybes_updated, maybes_archived}, asset_type="maybes_note", asset_id=maybes_id; headers carry tenant_id/user_id and optional episode_id. No Nexus logging by default; future mirroring uses nexus_doc_id via ingestion flow.

### Engines/Core/Connectors split
- northstar-core: model + service + HTTP APIs.
- northstar-engines: none.
- northstar-connectors: none.

### Open questions
- Filter/query semantics for list (tags? date ranges? search?).
- How origin_ref fields map to cards/surfaces.

### Tasks
- [x] B-MAYBES-01 – Define MaybesNote model (fields above) in planning doc for northstar-core and enforce asset_type="maybes_note". (Model fields locked in this section; asset_type fixed)
- [x] B-MAYBES-02 – Specify MaybesService methods and error semantics (auth/tenant ownership). (CRUD + canvas layout; auth/tenant required; archive vs delete)
- [x] B-MAYBES-03 – Plan HTTP APIs under /api/maybes (+ /api/maybes/canvas-layout) with payloads matching service. (GET list, POST create, PATCH update, DELETE archive, POST canvas-layout bulk)
- [x] B-MAYBES-04 – Define EventLog entries for maybes_created/updated/archived with tenant/user/asset IDs and optional episode linkage; no Nexus by default. (event_type set; asset_type="maybes_note")
- [x] B-MAYBES-05 – Decide on list filters (tags/search/date) and origin_ref shape alignment with surfaces/cards. (List filters to include tags/search/date optional; origin_ref {surface/app/thread_id/message_id?} reused)
- STATUS: PLANNING_READY_FOR_IMPLEMENTATION
- IMPLEMENTATION: initial backend/service/APIs/logging/tests added (2025-12-02)

## B-3D-PHASE-A – Scene Viewer planning (no implementation)

### Current state recap
- Service: FastAPI `/scene/build` in scene-engine expects `SceneBuildRequest { grid: {cols, rows, col_width, row_height}, boxes: [{id, x, y, z?, w, h, d?, kind, meta{}}], recipe: wall|vector_explorer }`.
- Output: `SceneBuildResult { scene: { sceneId, nodes: [{id, kind, gridBox3D{x,y,z,w,h,d}, worldPosition{x,y,z}, meta{}}], camera{position,target,mode} } }`.
- Recipes: `wall` and `vector_explorer` (uses `meta.vector` if present for placement).
- Known test issues: previously Pydantic rejected zero dims before normaliser; validators are Pydantic V1 style (warnings). Current tests are green after relaxing zero checks; keep note that validation vs normaliser interplay is delicate.

### Scene JSON contract (Phase A, FE-facing)
- Node required fields: `id`, `kind`, `worldPosition{x,y,z}`, `gridBox3D{x,y,z,w,h,d}`; `meta` map for labels/refs.
- Scene-level: `sceneId`, `nodes[]`, optional `camera` hint (position/target/mode); `grid` info can be attached as non-breaking addition.
- Non-breaking future additions: `materials`, `labels`, `cluster_id`, `render_config` (background/skybox), `lod_hint`.

### Integration with northstar-core
- Core exposes `SceneService.get_scene(app_id, recipe_id, tenant_id, options) -> Scene` (planning), calls engines `/scene/build` with tenant/env context and recipe params.
- Tenant/env flow: gateway injects tenant_id/env into request context; engines stay stateless aside from inputs.
- Logging: each scene build should emit ModelCall/PromptSnapshot (if agent-assisted) or EventLog entry with `scene_id`, `recipe`, `tenant_id`, `app_id`, optional `episode_id` for replay/trace; no Nexus writes unless explicitly requested later.

### Recipes and metadata
- Phase A recipes: `wall` (grid-aligned layout), `vector_explorer` (vector-based positioning using `meta.vector` or grid fallback).
- Node metadata for UI: `meta.title`/`meta.label` (tooltip), `meta.source_ref`/`card_ref`/`nexus_ref` to open cards/Nexus docs on click; optional `meta.thumbnail`/`meta.kind_detail` for icons.
- Reuse existing card/Nexus reference patterns; do not invent new link types.

### Selection & inspection plan
- Represent selection as `SceneSelectionEvent { scene_id, node_id, tenant_id, app_id?, episode_id? }`.
- Logging destination: EventLog (selection events) with linkage to Episode; Nexus only if explicitly mirrored (e.g., user adds note); optional dedicated 3D log stream can be planned later.
- Backend should return node meta sufficient for FE to request detail panes (e.g., card/nexus doc fetch) without embedding full payload in the scene.

### Open questions
- Camera defaults per recipe (orbit vs top-down) and whether to include render_config in response.
- Minimum required meta fields for click-through (card vs nexus ref) and standard naming.
- Should `grid` be returned as part of Scene for FE layout debugging?

### Blockers for implementation
- Decide logging shape for selection events (EventLog schema fields) and whether to add a specific event_type namespace.
- Confirm recipe parameterization (spacing/scale defaults) before exposing to core.
- Settle camera defaults so FE can render without guesswork.

---

### PLAN-0AM: DUAL-ENGINE MUSCLE STRATEGY (MESH + SOLID)

Status: PENDING
Owner: Antigravity
Area: engines/core-muscles
Summary: Implement two distinct geometry kernels to power specialized agents: one for artistic/creative mesh workflows (v1) and one for precision/CAD solid workflows (v1).

**Strategic Goal**
Build "Muscle Engines" that run headlessly and can be driven by atomic tokens from specialized agents.
- **Engine A (Mesh)**: High-speed, forgiving, artistic. For avatars, creative apps.
- **Engine B (Solid)**: Precision, manufacturable, rigid. For product design, architecture.

**Architecture**
Both engines expose an "Atomic Operation" API (stateless) that agents use to build/modify state.

#### ENGINE-024 – Mesh Muscle (Creative) v1
**Goal:** A lightweight Python/NumPy/Trimesh kernel for rapid organic modeling.
**Capabilities:**
- Primitive creation (Sphere, Box, Monkey).
- Subdivision (Catmull-Clark).
- Sculpting deformers (Move, Smooth, Inflate).
- Boolean (Approximate/Mesh-based).
**Stack:** Python + NumPy + Trimesh.

#### ENGINE-025 – Solid Muscle (Precision) v1
**Goal:** A robust CAD kernel wrapper for engineering precision.
**Capabilities:**
- BREP Primitives (Cylinder, Box, Cone).
- Boolean (Union, Difference, Intersection) - Exact.
- Fillet/Chamfer edges.
- Sketch Extrusion.
**Stack:** Binding to C++ Kernel (Manifold or OpenCascade - TBD).

**Tasks:**
- [ ] Scaffold `engines/mesh_kernel` and `engines/solid_kernel`.
- [ ] Define shared `AgentInstruction` schema (Token -> Operation).
- [ ] Implement V1 primitives for both.

### PLAN-AVATAR-BUILDER – Collaborative Avatar & Scene System (The "App")

- **Status**: PLANNING
- **Owner**: Antigravity
- **Area**: engines/avatar-builder
- **Summary**: A comprehensive roadmap to build a "Living Clay" application where Humans and AI co-create animated avatars in 3D worlds.
- **Detail**:
  - **Phase 1 (Mesh)**: Primitive/Sculpt muscles (DONE).
  - **Phase 2 (Paint)**: Material Engine for textures, shaders, and "skin" painting.
  - **Phase 3 (Bones)**: Rigging & Animation Engine for auto-rigging and playback.
  - **Phase 4 (Stage)**: Scene Engine extensions for props, lighting, and composition.
  - **Phase 5 (App)**: Collaborative Agent workflows (Vision -> Tokens -> Engines).
- **Artefacts**:
  - docs/plans/AVATAR_BUILDER_PLAN.md

### PLAN-GRIME-STUDIO – The "Full Gas" Showcase

- **Status**: PLANNING
- **Owner**: Antigravity
- **Area**: engines/showcase/grime-studio
- **Summary**: Build a hyper-realistic "recording studio" environment with 3 humanoid robots (DJ + 2 MCs) to demonstrate maximum engine capability.
- **Detail**:
  - **Environment**: Decks (CDJs), Mixer, Speakers, Mics (High Fidelity Props).
  - **Avatars**: 3 distinct robot rigs (Selecta_Bot, Spit_Bot_1, Spit_Bot_2).
  - **Animation**: Implement Inverse Kinematics (IK) for precise Mic-to-Mouth handling.
  - **Integration**: "Director Script" to orchestrate lighting, animation, and scene composition.
- **Artefacts**:
  - docs/plans/GRIME_STUDIO_PLAN.md


